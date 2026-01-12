# import json
import json
import logging
import os
import tempfile
import uuid
from datetime import datetime

from database import ConversionJob, get_db_session, Session
from database.models import LogEntry
from utils.enums.job_status import JobStatus
from sqlalchemy.orm.attributes import flag_modified
from database.utils import create_session, get_session, update_session_usage
from flask import jsonify, redirect, request, session
from utils.auth import require_session_auth
from utils.clerk_auth import get_optional_clerk_user_id
from utils.enums.device_profiles import DEVICE_PROFILES, DeviceProfile
from utils.globals import KCC_PATH, UPLOADS_DIRECTORY
# Import S3Storage lazily inside functions to avoid boto3 initialization before eventlet monkey patch
# from utils.storage.s3_storage import S3Storage
from utils.utils import process_conversion
from utils.enhanced_logger import setup_enhanced_logging, log_with_context
from utils.job_status import change_status
from utils.rate_limiter import rate_limit
# Import celery_app to call tasks by name (avoids circular import with tasks module)
from celery_config import celery_app
from utils.storage_migration import migrate_session_storage_async

logger = setup_enhanced_logging()


def has_active_jobs(db, exclude_job_id=None):
    """Check if there are any active jobs (processing or queued) excluding the given job_id."""
    active_statuses = [JobStatus.PROCESSING, JobStatus.QUEUED]
    query = db.query(ConversionJob).filter(ConversionJob.status.in_(active_statuses))
    
    if exclude_job_id:
        query = query.filter(ConversionJob.id != exclude_job_id)
    
    return query.count() > 0


def register_routes(app):
    # @app.before_request
    # def log_json_part_from_multipart():
    #     if request.content_type.startswith("multipart/form-data"):
    #         json_text = request.form.get("options")  # Adjust key if needed
    #         if json_text:
    #             try:
    #                 parsed = json.loads(json_text)
    #                 logging.info(
    #                     f"JSON from multipart field:\n{json.dumps(parsed, indent=2)}"
    #                 )
    #             except json.JSONDecodeError:
    #                 logging.warning(f"Invalid JSON in multipart field: {json_text}")
    #         else:
    #             logging.info("No JSON field 'data' found in multipart request")

    @app.route("/health", methods=["GET"])
    def health_check():
        """Health check endpoint."""
        return jsonify({"status": "healthy"}), 200

    # REMOVED: /api/user/stats endpoint - unused by frontend
    # User stats are available in Streamlit dashboard which queries DB directly
    # If needed in future, implement with Redis caching

    @app.route("/jobs", methods=["POST"])
    @rate_limit(max_requests=100, window_seconds=3600)  # 100 conversions per hour
    def create_job_with_upload():
        """Create a new job and return presigned upload URL in one call - INSTANT RESPONSE"""
        data = request.get_json()
        filename = data["filename"]
        file_size = data.get("file_size")
        device_profile = data.get("device_profile")
        advanced_options = data.get("advanced_options", {})

        # Get session key early (needed for immediate response)
        session_key = request.headers.get("X-Session-Key")
        if not session_key:
            return jsonify({"error": "No session key provided"}), 401

        # Validate file extension (fast - no DB/network)
        from utils.file_validation import validate_file_extension, UnsupportedFileFormatError
        try:
            validate_file_extension(filename)
        except UnsupportedFileFormatError as e:
            return jsonify({
                "error": e.message,
                "filename": filename
            }), 400

        # Validate advanced options for OTHER profile (fast - no DB/network)
        from utils.enums.advanced_options import validate_advanced_options
        validation_errors = validate_advanced_options(advanced_options, device_profile)
        if validation_errors:
            return jsonify({
                "error": "Invalid advanced options",
                "validation_errors": validation_errors
            }), 400

        # OPTIMIZATION: Create job_id immediately and store in Redis (instant: <1ms)
        # Redis provides fast access during upload/processing
        # DB persistence happens only when job reaches terminal state
        job_id = str(uuid.uuid4())
        storage_id = session_key
        key = f"{storage_id}/{job_id}/input/{filename}"

        # Prepare job data for Redis
        from datetime import datetime
        current_time = datetime.utcnow()

        job_data = {
            'id': job_id,
            'status': 'UPLOADING',
            'input_filename': filename,
            'file_size': file_size,
            'device_profile': device_profile,
            'session_key': session_key,
            'upload_progress_bytes': 0,
            'uploading_at': current_time,
            'created_at': current_time,
            's3_key': key,
            # Atomized options - set defaults if not provided
            'manga_style': advanced_options.get('manga_style', False) if advanced_options else False,
            'hq': advanced_options.get('hq', False) if advanced_options else False,
            'two_panel': advanced_options.get('two_panel', False) if advanced_options else False,
            'webtoon': advanced_options.get('webtoon', False) if advanced_options else False,
            'no_processing': advanced_options.get('no_processing', False) if advanced_options else False,
            'upscale': advanced_options.get('upscale', False) if advanced_options else False,
            'stretch': advanced_options.get('stretch', False) if advanced_options else False,
            'autolevel': advanced_options.get('autolevel', False) if advanced_options else False,
            'black_borders': advanced_options.get('black_borders', False) if advanced_options else False,
            'white_borders': advanced_options.get('white_borders', False) if advanced_options else False,
            'force_color': advanced_options.get('force_color', False) if advanced_options else False,
            'force_png': advanced_options.get('force_png', False) if advanced_options else False,
            'mozjpeg': advanced_options.get('mozjpeg', False) if advanced_options else False,
            'no_kepub': advanced_options.get('no_kepub', False) if advanced_options else False,
            'spread_shift': advanced_options.get('spread_shift', False) if advanced_options else False,
            'no_rotate': advanced_options.get('no_rotate', False) if advanced_options else False,
            'rotate_first': advanced_options.get('rotate_first', False) if advanced_options else False,
            'target_size': advanced_options.get('target_size') if advanced_options else None,
            'splitter': advanced_options.get('splitter', 0) if advanced_options else 0,
            'cropping': advanced_options.get('cropping', 0) if advanced_options else 0,
            'custom_width': advanced_options.get('custom_width') if advanced_options else None,
            'custom_height': advanced_options.get('custom_height') if advanced_options else None,
            'gamma': advanced_options.get('gamma') if advanced_options else None,
            'cropping_power': advanced_options.get('cropping_power', 1) if advanced_options else 1,
            'preserve_margin': advanced_options.get('preserve_margin', 0) if advanced_options else 0,
            'author': advanced_options.get('author', 'KCC') if advanced_options else 'KCC',
            'title': advanced_options.get('title') if advanced_options else None,
            'output_format': advanced_options.get('output_format') if advanced_options else None,
        }

        # Store job in Redis immediately (< 1ms)
        from utils.redis_job_store import RedisJobStore
        success = RedisJobStore.create_job(job_id, job_data)

        if not success:
            log_with_context(
                logger, 'error', 'Failed to create job in Redis',
                job_id=job_id,
                filename=filename
            )
            return jsonify({"error": "Failed to create job"}), 500

        log_with_context(
            logger, 'info', '\n\n=== JOB CREATED IN REDIS ===\n\n',
            job_id=job_id,
            user_id=session_key,
            filename=filename,
            device_profile=device_profile,
            status='uploading',
            s3_key=key,
            storage='redis',
            flow_step='job_creation_instant'
        )

        # WARMUP: Trigger VM provisioning during upload (not after) for faster processing
        # Signals KEDA to scale workers while file uploads, reducing wait time by 1-2 minutes
        try:
            from utils.redis_job_store import redis_client
            if redis_client:
                redis_client.lpush('pending_work', job_id)
                redis_client.expire('pending_work', 3600)  # Auto-cleanup after 1 hour
                log_with_context(
                    logger, 'info', 'Job queued for worker warmup during upload',
                    job_id=job_id
                )
        except Exception as e:
            # Non-critical - continue even if warmup fails
            log_with_context(
                logger, 'warning', 'Failed to queue warmup',
                job_id=job_id,
                error=str(e)
            )

        # Note: R2 doesn't support presigned POST - we'll use multipart upload instead
        # Frontend should call /jobs/{job_id}/multipart/initiate after creating the job

        # Background thread for session validation + Clerk auth (doesn't block response)
        import threading

        # Capture Clerk user ID in request context BEFORE starting thread
        from utils.clerk_auth import get_optional_clerk_user_id
        clerk_user_id_captured = None
        try:
            clerk_user_id_captured = get_optional_clerk_user_id()
        except Exception:
            pass  # Ignore errors - Clerk auth is optional

        def validate_session_and_link_user_async():
            """Validate session and auto-link to authenticated user if needed"""
            db = get_db_session()
            try:
                # STEP 1: Validate session exists in database
                from database.utils import get_session, update_session_usage
                session_obj = get_session(db, session_key)

                if not session_obj:
                    # Invalid session - mark job as ERRORED
                    log_with_context(
                        logger, 'error', 'Invalid session key detected (async validation failed)',
                        job_id=job_id,
                        session_key=session_key[:8] + '...'
                    )
                    from utils.redis_job_store import RedisJobStore
                    RedisJobStore.update_job(job_id, {
                        'status': 'ERRORED',
                        'error_message': 'Invalid session key. Please refresh the page.',
                        'errored_at': datetime.utcnow()
                    })
                    return

                # STEP 2: Update session last_used_at timestamp
                update_session_usage(db, session_key)

                # STEP 3: Auto-link to authenticated user if needed
                if clerk_user_id_captured and session_obj.is_anonymous:
                    from database.utils import get_or_create_user
                    user = get_or_create_user(db, clerk_user_id_captured)
                    session_obj.user_id = user.id
                    session_obj.claimed_at = datetime.utcnow()
                    db.commit()

                    log_with_context(
                        logger, 'warning', '⚠️ Auto-linked session to authenticated user (async)',
                        user_id=clerk_user_id_captured,
                        session_key=session_obj.session_key,
                        user_db_id=user.id,
                        job_id=job_id
                    )

                log_with_context(
                    logger, 'info', 'Session validation completed (async)',
                    job_id=job_id,
                    session_valid=True
                )

            except Exception as e:
                db.rollback()
                log_with_context(
                    logger, 'error', f'Session validation failed (async): {str(e)}',
                    job_id=job_id
                )
                # Mark job as ERRORED
                from utils.redis_job_store import RedisJobStore
                RedisJobStore.update_job(job_id, {
                    'status': 'ERRORED',
                    'error_message': 'Session validation failed. Please try again.',
                    'errored_at': datetime.utcnow()
                })
            finally:
                db.close()

        # Start background thread (non-blocking)
        thread = threading.Thread(target=validate_session_and_link_user_async, daemon=True)
        thread.start()

        # Return job info immediately - Redis write is instant (<1ms)
        # Frontend can start multipart upload immediately
        return jsonify({
            "job_id": job_id,
            "status": "uploading",
            "message": "Job created. Call /jobs/{job_id}/multipart/initiate to start upload."
        })

    # ============================================================================
    # REMOVED: /jobs/<job_id>/upload-chunk endpoint (Lines 269-569, ~300 lines)
    # ============================================================================
    #
    # **Reason for removal:**
    # - NOT used by modern frontend (verified via codebase search)
    # - Frontend uses direct S3 multipart uploads instead
    # - Had critical performance issues:
    #   * Line 309: DB query on every chunk upload
    #   * Line 366-372: db.commit() on every chunk (DB connection pool exhaustion)
    # - Same issue as the fixed handle_upload_progress bug
    #
    # **Modern upload flow:**
    # 1. POST /jobs - Create job in Redis
    # 2. POST /jobs/{id}/multipart/initiate - Get presigned URLs from S3
    # 3. Frontend uploads directly to S3 (no backend involvement)
    # 4. POST /jobs/{id}/multipart/complete-part - Mark parts complete (Redis only)
    # 5. POST /jobs/{id}/multipart/finalize - Transition to QUEUED, persist to DB
    #
    # If chunked uploads are needed in future, implement using Redis-only pattern.
    # ============================================================================

    @app.route("/jobs/<job_id>/start", methods=["PATCH"])
    @require_session_auth
    def start_job_processing(job_id, session_obj=None):
        """Start processing after upload is complete"""
        log_with_context(
            logger, 'info', 'Processing start request received',
            job_id=job_id,
            user_id=request.headers.get("X-Session-Key"),
            endpoint='/jobs/{}/start'.format(job_id)
        )
        
        session_key = request.headers.get("X-Session-Key")
        if not session_key:
            return jsonify({"error": "No session key provided"}), 401

        db = get_db_session()
        try:
            # Get the job
            job = db.query(ConversionJob).get(job_id)
            if not job:
                return jsonify({"error": "Job not found"}), 404
            
            if job.session_key != session_key:
                return jsonify({"error": "Unauthorized"}), 403
            
            if job.status != JobStatus.UPLOADING:
                return jsonify({"error": f"Job is in {job.status.value} status, expected uploading"}), 400
            
            # Set upload progress to file size in bytes (upload complete)
            upload_bytes = job.input_file_size or 0
            job.upload_progress_bytes = upload_bytes

            log_with_context(
                logger, 'info', '=== UPLOAD COMPLETED - STARTING PROCESSING ===',
                job_id=job_id,
                user_id=session_key,
                filename=job.input_filename,
                upload_progress_bytes=upload_bytes,
                flow_step='upload_complete'
            )

            # Update job to queued and start processing
            change_status(job, JobStatus.QUEUED, db, session_key, {
                'action': 'start_processing',
                'upload_progress_bytes': upload_bytes,
                'flow_step': 'queue_for_processing'
            })
            
        except Exception as e:
            db.rollback()
            log_with_context(
                logger, 'error', f'Failed to start job processing: {str(e)}',
                job_id=job_id,
                user_id=session_key,
                error_type=type(e).__name__
            )
            return jsonify({"error": "Failed to start processing"}), 500
        finally:
            db.close()

        # Start background processing immediately
        def background_conversion():
            try:
                log_with_context(
                    logger, 'info', '=== BACKGROUND THREAD STARTED ===',
                    job_id=job_id,
                    user_id=session_key,
                    flow_step='background_thread_start'
                )
                
                # Get job details for processing
                db = get_db_session()
                try:
                    job = db.query(ConversionJob).get(job_id)
                    if not job:
                        log_with_context(
                            logger, 'error', 'Job not found in background thread',
                            job_id=job_id,
                            user_id=session_key
                        )
                        return
                    
                    # Use session_key as the storage prefix for consistency
                    storage_id = session_key
                        
                finally:
                    db.close()

                # Construct paths
                temp_dir = os.path.join(UPLOADS_DIRECTORY, job_id, "input")
                os.makedirs(temp_dir, exist_ok=True)
                local_file_path = os.path.join(temp_dir, job.input_filename)
                s3_key = f"{storage_id}/{job_id}/input/{job.input_filename}"

                # Download from S3
                s3_storage = S3Storage()
                log_with_context(
                    logger, 'info', '=== BACKGROUND PROCESSING STARTED ===',
                    job_id=job_id,
                    user_id=session_key,
                    s3_key=s3_key,
                    flow_step='background_processing_start'
                )

                # First, check if the file exists and list what's actually there
                try:
                    log_with_context(
                        logger, 'info', 'Checking if S3 key exists',
                        job_id=job_id,
                        user_id=session_key,
                        s3_key=s3_key
                    )
                    if not s3_storage.exists(s3_key):
                        # List what's actually in the alias/job_id prefix
                        prefix = f"{storage_id}/{job_id}/"
                        available_keys = s3_storage.list(prefix)
                        log_with_context(
                            logger, 'error', f'S3 key not found. Available keys under prefix {prefix}',
                            job_id=job_id,
                            user_id=session_key,
                            expected_key=s3_key,
                            prefix=prefix,
                            available_keys=available_keys
                        )
                        raise Exception(f"File not found in S3. Expected: {s3_key}, Available: {available_keys}")
                    else:
                        log_with_context(
                            logger, 'info', 'S3 key exists, proceeding with download',
                            job_id=job_id,
                            user_id=session_key,
                            s3_key=s3_key
                        )
                except Exception as check_error:
                    log_with_context(
                        logger, 'error', f'Error checking S3 key: {str(check_error)}',
                        job_id=job_id,
                        user_id=session_key,
                        s3_key=s3_key,
                        error_type=type(check_error).__name__
                    )
                    raise

                s3_storage.client.download_file(s3_storage.bucket, s3_key, local_file_path)
                
                log_with_context(
                    logger, 'info', '=== S3 DOWNLOAD COMPLETED - STARTING CONVERSION ===',
                    job_id=job_id,
                    user_id=session_key,
                    file_size=os.path.getsize(local_file_path) if os.path.exists(local_file_path) else 0,
                    local_path=local_file_path,
                    flow_step='conversion_start'
                )

                # Get conversion options from atomized columns
                advanced_options = job.get_options_dict()
                options = {"advanced_options": advanced_options}
                process_conversion(job_id, job.input_filename, session_key, options, job.device_profile, alias)
                
            except Exception as e:
                log_with_context(
                    logger, 'error', f'Background processing failed: {str(e)}',
                    job_id=job_id,
                    user_id=session_key,
                    error_type=type(e).__name__
                )
                
                # Store errored input file in error bucket for debugging via Celery
                try:
                    input_key = f"{storage_id}/{job_id}/input/{job.input_filename}"
                    error_key = f"errors/{alias}/{job_id}/input/{job.input_filename}"
                    celery_app.send_task('tasks.s3_copy_to_error_bucket', args=[input_key, error_key], queue='s3_tasks')
                    
                    log_with_context(
                        logger, 'info', f'Errored file stored in error bucket: {error_key}',
                        job_id=job_id,
                        user_id=session_key,
                        error_bucket_key=error_key
                    )
                except Exception as storage_error:
                    log_with_context(
                        logger, 'warning', f'Failed to store errored file in error bucket: {storage_error}',
                        job_id=job_id,
                        user_id=session_key
                    )
                
                # Update job status to errored
                db = get_db_session()
                try:
                    job = db.query(ConversionJob).get(job_id)
                    if job:
                        change_status(job, JobStatus.ERRORED, db, session_key, {
                            'error_source': 'background_processing'
                        })
                except Exception:
                    db.rollback()
                finally:
                    db.close()
        
        # Phase 3: Queue task to Celery (threading removed)
        try:
            # Queue the Celery task
            async_result = celery_app.send_task('mangaconverter.convert_file', kwargs={
                "job_id": job_id,
                "upload_name": job.input_filename,
                "session_key": session_key,
                "options": {"advanced_options": job.get_options_dict()},
                "device_profile": job.device_profile,
                "alias": storage_id
            })

            # Store task_id for potential revocation (e.g., job abandonment)
            job.celery_task_id = async_result.id
            db.commit()

            log_with_context(
                logger, 'info', '=== JOB QUEUED IN CELERY ===',
                job_id=job_id,
                user_id=session_key,
                task_id=async_result.id,
                flow_step='celery_task_queued'
            )

        except Exception as celery_error:
            log_with_context(
                logger, 'error', f'Failed to queue Celery task: {str(celery_error)}',
                job_id=job_id,
                user_id=session_key,
                error_type=type(celery_error).__name__
            )
            return jsonify({"error": "Failed to queue task"}), 500

        # Background processing started, responding immediately

        return jsonify({"success": True, "status": "queued"}), 202

    @app.route("/jobs/<job_id>/cancel", methods=["POST"])
    @require_session_auth
    def cancel_job(job_id, session_obj=None):
        """Cancel a running or queued job"""
        session_key = request.headers.get("X-Session-Key")

        from utils.redis_job_store import RedisJobStore, acquire_cancellation_lock, release_cancellation_lock, has_active_cancellation
        from datetime import datetime

        log_with_context(
            logger, 'info', 'Job cancellation request received',
            job_id=job_id,
            user_id=session_key,
            endpoint='/jobs/{}/cancel'.format(job_id)
        )

        # Check if another cancellation is already in progress for this session
        active_cancellation = has_active_cancellation(session_key)
        if active_cancellation:
            log_with_context(
                logger, 'warning', 'Cancellation blocked: another cancellation in progress',
                job_id=job_id,
                user_id=session_key,
                active_cancellation_job=active_cancellation
            )
            return jsonify({
                "error": "Another cancellation is in progress",
                "active_job_id": active_cancellation,
                "message": "Please wait for the current cancellation to complete"
            }), 429

        # Acquire cancellation lock for this session
        if not acquire_cancellation_lock(session_key, job_id):
            log_with_context(
                logger, 'warning', 'Failed to acquire cancellation lock',
                job_id=job_id,
                user_id=session_key
            )
            return jsonify({
                "error": "Failed to acquire cancellation lock",
                "message": "Another cancellation started at the same time"
            }), 429

        try:
            # Check Redis first (UPLOADING/QUEUED jobs)
            redis_job = RedisJobStore.get_job(job_id)
            if redis_job:
                # Job is in Redis
                if redis_job.get('session_key') != session_key:
                    release_cancellation_lock(session_key, job_id)
                    log_with_context(
                        logger, 'warning', 'Unauthorized cancellation attempt (Redis job)',
                        job_id=job_id,
                        user_id=session_key
                    )
                    return jsonify({"error": "Unauthorized"}), 403

                previous_status = redis_job.get('status')

                # Cancel the job in Redis and mark as dismissed for immediate filtering
                now_ts = datetime.utcnow()
                RedisJobStore.update_job(job_id, {
                    'status': 'CANCELLED',
                    'cancelled_at': now_ts,
                    'dismissed_at': now_ts,
                })

                # Persist to DB (CANCELLED is terminal)
                job_data = RedisJobStore.get_job(job_id)
                if job_data:
                    RedisJobStore.persist_to_db(job_id, job_data)

                    # Broadcast CANCELLED status to WebSocket clients
                    from utils.websocket import broadcast_job_status
                    broadcast_job_status(job_id, {
                        'status': 'CANCELLED',
                        'job_id': job_id,
                        'message': 'Job cancelled by user',
                        'dismissed_at': now_ts.isoformat() if hasattr(now_ts, 'isoformat') else str(now_ts)
                    })

                log_with_context(
                    logger, 'info', 'Job cancelled (Redis)',
                    job_id=job_id,
                    user_id=session_key,
                    previous_status=previous_status,
                    new_status='CANCELLED'
                )

                # Release lock before returning
                release_cancellation_lock(session_key, job_id)

                return jsonify({
                    "status": "CANCELLED",
                    "message": "Job cancelled successfully"
                }), 200

            # Not in Redis - check DB (PROCESSING/COMPLETE/etc)
            db = get_db_session()
            try:
                job = db.query(ConversionJob).get(job_id)
                if not job:
                    release_cancellation_lock(session_key, job_id)
                    return jsonify({"error": "Job not found"}), 404

                if job.session_key != session_key:
                    release_cancellation_lock(session_key, job_id)
                    log_with_context(
                        logger, 'warning', 'Unauthorized cancellation attempt (DB job)',
                        job_id=job_id,
                        user_id=session_key,
                        job_owner=job.session_key
                    )
                    return jsonify({"error": "Unauthorized"}), 403

                previous_status = job.status.value

                # If job is PROCESSING, cancel it
                if job.status == JobStatus.PROCESSING:
                    change_status(job, JobStatus.CANCELLED, db, session_key, {
                        'cancellation_reason': 'user_requested',
                        'previous_status': previous_status,
                        'cancelled_by': 'user'
                    })

                # Also mark as dismissed so clients drop it immediately on reload
                if not getattr(job, 'dismissed_at', None):
                    from datetime import datetime as _dt
                    job.dismissed_at = _dt.utcnow()
                    db.commit()

                log_with_context(
                    logger, 'info', 'Job cancellation processed (DB)',
                    job_id=job_id,
                    user_id=session_key,
                    previous_status=previous_status,
                    new_status=job.status.value
                )

                # Best-effort broadcast so connected clients update immediately
                try:
                    from utils.websocket import broadcast_job_status
                    dismissed_iso = job.dismissed_at.isoformat() if hasattr(job.dismissed_at, 'isoformat') else str(job.dismissed_at)
                    broadcast_job_status(job_id, {
                        'status': job.status.value,
                        'job_id': job_id,
                        'message': 'Job cancelled by user',
                        'dismissed_at': dismissed_iso,
                    })
                except Exception as bcast_err:
                    logger.warning(f"Failed to broadcast cancellation for job {job_id}: {bcast_err}")

                # Release lock before returning
                release_cancellation_lock(session_key, job_id)

                return jsonify({
                    "status": job.status.value,
                    "message": "Job cancellation processed"
                }), 200

            except Exception as e:
                db.rollback()
                release_cancellation_lock(session_key, job_id)
                log_with_context(
                    logger, 'error', f'Failed to cancel job: {str(e)}',
                    job_id=job_id,
                    user_id=session_key,
                    error=str(e),
                    error_type=type(e).__name__
                )
                return jsonify({"error": str(e)}), 500
            finally:
                db.close()

        except Exception as e:
            # Outer exception handler for Redis/general errors
            release_cancellation_lock(session_key, job_id)
            log_with_context(
                logger, 'error', f'Failed to cancel job (outer): {str(e)}',
                job_id=job_id,
                user_id=session_key,
                error=str(e),
                error_type=type(e).__name__
            )
            return jsonify({"error": str(e)}), 500

    @app.route("/jobs/<job_id>/dismiss", methods=["POST"])
    @require_session_auth
    def dismiss_job(job_id, session_obj=None):
        """Mark a COMPLETE or DOWNLOADED job as dismissed (sets dismissed_at)."""
        from utils.redis_job_store import RedisJobStore
        from datetime import datetime
        # Import here to avoid circulars and keep function-local
        from utils.websocket import broadcast_job_status
        session_key = session_obj.session_key if session_obj else None

        db = get_db_session()
        try:
            job = db.query(ConversionJob).get(job_id)
            if not job:
                return jsonify({"error": "Job not found"}), 404

            if job.session_key != session_key:
                return jsonify({"error": "Unauthorized"}), 403

            # Only allow dismissing COMPLETE or DOWNLOADED jobs
            if job.status not in [JobStatus.COMPLETE, JobStatus.DOWNLOADED]:
                return jsonify({"error": f"Job is in {job.status.value} status; only COMPLETE or DOWNLOADED can be dismissed"}), 400

            if not job.dismissed_at:
                job.dismissed_at = datetime.utcnow()
                db.commit()

            # Update Redis snapshot if present (so session_update reflects dismissal flag)
            redis_job = RedisJobStore.get_job(job_id)
            if redis_job:
                RedisJobStore.update_job(job_id, { 'dismissed_at': job.dismissed_at })

            log_with_context(
                logger, 'info', 'Job dismissed (DB)',
                job_id=job_id,
                user_id=session_key,
                status=job.status.value,
                dismissed=True
            )

            # Immediately broadcast session update so clients drop dismissed job from UI
            try:
                broadcast_job_status(job_id, {
                    'status': job.status.value,
                    'dismissed_at': job.dismissed_at.isoformat() if hasattr(job.dismissed_at, 'isoformat') else str(job.dismissed_at)
                })
            except Exception as bcast_err:
                logger.warning(f"Failed to broadcast dismissal for job {job_id}: {bcast_err}")

            return jsonify({
                "status": job.status.value,
                "dismissed": True,
                "message": "Job dismissed successfully"
            }), 200
        except Exception as e:
            db.rollback()
            log_with_context(
                logger, 'error', f'Failed to dismiss job: {str(e)}',
                job_id=job_id,
                user_id=session_key,
                error=str(e),
                error_type=type(e).__name__
            )
            return jsonify({"error": str(e)}), 500
        finally:
            db.close()

    @app.route("/register", methods=["GET"])
    def generate_session():
        """Generate and return a new session key for frontend authentication"""
        try:
            # Generate a new UUID as session key
            session_key = str(uuid.uuid4())
            
            log_with_context(
                logger, 'info', 'Generated new session key',
                user_id=session_key,
                client_ip=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')[:100]  # Truncate long user agents
            )

            # Store the session key in the database
            db = get_db_session()
            try:
                log_with_context(
                    logger, 'info', 'Creating session in database',
                    user_id=session_key
                )
                # First check if the session already exists
                existing_session = get_session(db, session_key)
                if existing_session:
                    log_with_context(
                        logger, 'info', 'Session already exists, returning it',
                        user_id=session_key,
                        alias=existing_session.alias
                    )
                    session["session_key"] = session_key
                    return jsonify({"success": True, "session_key": session_key}), 200

                # Create a new session with user agent
                user_agent = request.headers.get('User-Agent')
                create_session(db, session_key, user_agent=user_agent)
                log_with_context(
                    logger, 'info', 'Successfully created session in database',
                    user_id=session_key
                )

                # Store the session key in the session
                session["session_key"] = session_key
                return jsonify({"success": True, "session_key": session_key}), 200
            except Exception as db_error:
                log_with_context(
                    logger, 'error', f'Database error while creating session: {str(db_error)}',
                    user_id=session_key,
                    error_type=type(db_error).__name__
                )
                # Still return the session key even if DB storage fails
                return jsonify({"success": True, "session_key": session_key}), 200
            finally:
                db.close()
        except Exception as e:
            log_with_context(
                logger, 'error', f'Error generating session key: {str(e)}',
                error_type=type(e).__name__
            )
            return (
                jsonify({"success": False, "error": "Failed to generate session key"}),
                500,
            )

    @app.route("/api/auth/claim-session", methods=["POST"])
    def claim_session():
        """
        Link an anonymous session to an authenticated Clerk user.
        This is called when a user signs up/signs in and wants to claim their existing jobs.
        """
        from utils.clerk_auth import get_clerk_user_id_from_request
        from datetime import datetime
        import uuid

        clerk_user_id = get_clerk_user_id_from_request()
        if not clerk_user_id:
            return jsonify({
                "success": False,
                "error": "Authentication required. Please sign in with Clerk."
            }), 401

        # Get the anonymous session key from request body
        data = request.get_json()
        anonymous_session_key = data.get("session_key")
        email = data.get("email")
        first_name = data.get("first_name")
        last_name = data.get("last_name")

        log_with_context(
            logger, 'info', f'Received claim-session request',
            user_id=clerk_user_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            has_email=bool(email)
        )

        if not anonymous_session_key:
            return jsonify({
                "success": False,
                "error": "No session key provided to claim."
            }), 400

        db = get_db_session()
        try:
            # Create or update user in users table
            from database.utils import get_or_create_user
            user = get_or_create_user(db, clerk_user_id, email, first_name, last_name)
            log_with_context(
                logger, 'info', f'User record created/updated',
                user_id=clerk_user_id,
                user_db_id=user.id,
                email=email
            )

            # Find the anonymous session
            from database import Session
            anonymous_session = db.query(Session).filter_by(session_key=anonymous_session_key).first()

            if not anonymous_session:
                # Anonymous session doesn't exist (was deleted or never existed)
                # Check if user already has a session, otherwise create one
                log_with_context(
                    logger, 'info', 'Anonymous session not found, checking for existing user session',
                    user_id=clerk_user_id,
                    anonymous_session=anonymous_session_key
                )

                existing_user_session = db.query(Session).filter_by(user_id=user.id).first()

                if existing_user_session:
                    # User already has a session, return it
                    return jsonify({
                        "success": True,
                        "message": "Using existing user session.",
                        "session_key": existing_user_session.session_key
                    }), 200
                else:
                    # Create a new session for the user
                    new_session_key = str(uuid.uuid4())
                    user_agent = request.headers.get('User-Agent')
                    create_session(db, new_session_key, user_agent=user_agent)
                    new_session = db.query(Session).filter_by(session_key=new_session_key).first()
                    new_session.user_id = user.id
                    new_session.claimed_at = datetime.utcnow()
                    db.commit()

                    log_with_context(
                        logger, 'info', 'Created new session for user',
                        user_id=clerk_user_id,
                        new_session_key=new_session_key
                    )

                    return jsonify({
                        "success": True,
                        "message": "New session created for user.",
                        "session_key": new_session_key
                    }), 201

            # Check if session is already claimed
            if not anonymous_session.is_anonymous:
                if anonymous_session.user_id == user.id:
                    # User is claiming their own session again (idempotent)
                    return jsonify({
                        "success": True,
                        "message": "Session already claimed by this user.",
                        "session_key": anonymous_session.session_key
                    }), 200
                else:
                    # Session belongs to another user
                    return jsonify({
                        "success": False,
                        "error": "Session already claimed by another user."
                    }), 400

            # Check if user already has a session
            existing_user_session = db.query(Session).filter_by(user_id=user.id).first()

            if existing_user_session:
                # User already has a session - merge jobs from anonymous session
                log_with_context(
                    logger, 'info', f'Merging {len(anonymous_session.conversion_jobs)} jobs from anonymous session to existing user session',
                    user_id=clerk_user_id,
                    anonymous_session=anonymous_session_key,
                    user_session=existing_user_session.session_key
                )

                # Store old alias for storage migration before deleting session
                old_alias = anonymous_session.alias

                jobs_merged = len(anonymous_session.conversion_jobs)
                for job in anonymous_session.conversion_jobs:
                    job.session_key = existing_user_session.session_key

                # Delete the anonymous session
                db.delete(anonymous_session)
                db.commit()

                # Trigger async storage path migration for the merged jobs
                # Since jobs now belong to existing_user_session, migrate from old alias to email
                if email and old_alias:
                    # Use the existing user session key since jobs were moved there
                    migrate_session_storage_async(existing_user_session.session_key, old_alias, email)
                    log_with_context(
                        logger, 'info', 'Triggered storage path migration after job merge',
                        session_key=existing_user_session.session_key,
                        old_alias=old_alias,
                        new_email=email,
                        jobs_merged=jobs_merged
                    )

                return jsonify({
                    "success": True,
                    "message": "Jobs merged successfully.",
                    "session_key": existing_user_session.session_key,
                    "jobs_merged": jobs_merged
                }), 200
            else:
                # Claim the anonymous session for this user
                log_with_context(
                    logger, 'info', 'Claiming anonymous session for Clerk user',
                    user_id=clerk_user_id,
                    session_key=anonymous_session_key
                )

                # Store old alias for storage migration
                old_alias = anonymous_session.alias

                anonymous_session.user_id = user.id
                anonymous_session.claimed_at = datetime.utcnow()
                db.commit()

                # Trigger async storage path migration from alias to email
                if email and old_alias:
                    migrate_session_storage_async(anonymous_session_key, old_alias, email)
                    log_with_context(
                        logger, 'info', 'Triggered storage path migration',
                        session_key=anonymous_session_key,
                        old_alias=old_alias,
                        new_email=email
                    )

                return jsonify({
                    "success": True,
                    "message": "Session claimed successfully.",
                    "session_key": anonymous_session.session_key
                }), 200

        except Exception as e:
            db.rollback()
            log_with_context(
                logger, 'error', f'Error claiming session: {str(e)}',
                user_id=clerk_user_id,
                session_key=anonymous_session_key,
                error_type=type(e).__name__
            )
            return jsonify({
                "success": False,
                "error": "Failed to claim session."
            }), 500
        finally:
            db.close()

    @app.route("/api/auth/get-or-create-session", methods=["POST"])
    def get_or_create_session():
        """
        Get or create a session for a Clerk user.
        If user is authenticated, returns their claimed session or creates a new one.
        If user is anonymous, creates a new anonymous session.
        """
        clerk_user_id = get_optional_clerk_user_id()

        # Get user info from request body
        data = request.get_json() or {}
        email = data.get("email")
        first_name = data.get("first_name")
        last_name = data.get("last_name")

        log_with_context(
            logger, 'info', f'Received get-or-create-session request',
            user_id=clerk_user_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            has_email=bool(email)
        )

        db = get_db_session()

        try:
            from database import Session
            from database.utils import get_or_create_user

            if clerk_user_id:
                # Create or update user in users table
                user = get_or_create_user(db, clerk_user_id, email, first_name, last_name)
                log_with_context(
                    logger, 'info', f'User record created/updated',
                    user_id=clerk_user_id,
                    user_db_id=user.id,
                    email=email
                )

                # Authenticated user - find or create their session
                user_session = db.query(Session).filter_by(user_id=user.id).first()

                if user_session:
                    log_with_context(
                        logger, 'info', 'Returning existing session for Clerk user',
                        user_id=clerk_user_id,
                        session_key=user_session.session_key
                    )
                    return jsonify({
                        "success": True,
                        "session_key": user_session.session_key,
                        "is_anonymous": False
                    }), 200
                else:
                    # Create new session for authenticated user
                    session_key = str(uuid.uuid4())
                    user_agent = request.headers.get('User-Agent')
                    create_session(db, session_key, user_agent=user_agent)

                    # Immediately claim it for this user
                    new_session = db.query(Session).filter_by(session_key=session_key).first()
                    new_session.user_id = user.id
                    new_session.claimed_at = datetime.utcnow()
                    db.commit()

                    log_with_context(
                        logger, 'info', 'Created new session for Clerk user',
                        user_id=clerk_user_id,
                        session_key=session_key
                    )

                    return jsonify({
                        "success": True,
                        "session_key": session_key,
                        "is_anonymous": False
                    }), 201
            else:
                # Anonymous user - create new anonymous session
                session_key = str(uuid.uuid4())
                user_agent = request.headers.get('User-Agent')
                create_session(db, session_key, user_agent=user_agent)

                log_with_context(
                    logger, 'info', 'Created new anonymous session',
                    session_key=session_key
                )

                return jsonify({
                    "success": True,
                    "session_key": session_key,
                    "is_anonymous": True
                }), 201

        except Exception as e:
            db.rollback()
            log_with_context(
                logger, 'error', f'Error getting/creating session: {str(e)}',
                user_id=clerk_user_id,
                error_type=type(e).__name__
            )
            return jsonify({
                "success": False,
                "error": "Failed to get or create session."
            }), 500
        finally:
            db.close()

    @app.route("/api/auth/delete-user", methods=["DELETE"])
    def delete_user_account():
        """
        Delete a user and all their session associations.
        This is called after a user deletes their Clerk account.
        """
        from utils.clerk_auth import get_clerk_user_id_from_request

        clerk_user_id = get_clerk_user_id_from_request()
        if not clerk_user_id:
            return jsonify({
                "success": False,
                "error": "Authentication required. Please sign in with Clerk."
            }), 401

        db = get_db_session()
        try:
            from database import User, Session

            # Find the user
            user = db.query(User).filter_by(clerk_user_id=clerk_user_id).first()

            if not user:
                return jsonify({
                    "success": False,
                    "error": "User not found."
                }), 404

            # Delete all user sessions first (since Session has FK to User)
            db.query(Session).filter_by(user_id=user.id).delete()

            # Delete user
            db.delete(user)
            db.commit()

            log_with_context(
                logger, 'info', 'User account and associations deleted',
                user_id=clerk_user_id,
                user_db_id=user.id
            )

            return jsonify({
                "success": True,
                "message": "User account deleted successfully."
            }), 200

        except Exception as e:
            db.rollback()
            log_with_context(
                logger, 'error', f'Error deleting user: {str(e)}',
                user_id=clerk_user_id,
                error_type=type(e).__name__
            )
            return jsonify({
                "success": False,
                "error": "Failed to delete user account."
            }), 500
        finally:
            db.close()


    @app.route("/status/<job_id>", methods=["GET"])
    @require_session_auth
    def check_status(job_id, session_obj=None):
        from datetime import datetime

        # Status poll request (no logging needed - too frequent)
        # NOTE: Abandonment detection now handled by WebSocket disconnect events

        db = get_db_session()
        try:
            job = db.query(ConversionJob).get(job_id)
            if job:
                from database.models import format_bytes

                response = {
                    "status": job.status.value,
                    "projected_eta": job.projected_eta,
                    "projected_eta_minutes": round(job.projected_eta / 60, 1) if job.projected_eta else None,
                    "upload_progress_bytes": job.upload_progress_bytes if hasattr(job, 'upload_progress_bytes') else 0,
                    "upload_progress_formatted": format_bytes(job.upload_progress_bytes) if hasattr(job, 'upload_progress_bytes') and job.upload_progress_bytes else None,
                }

                # Add elapsed time if job is processing
                if job.status == JobStatus.PROCESSING and job.created_at:
                    from datetime import datetime
                    elapsed = (datetime.utcnow() - job.created_at).total_seconds()
                    response["elapsed_seconds"] = int(elapsed)

                    # Calculate remaining time
                    if job.projected_eta:
                        remaining = max(0, job.projected_eta - elapsed)
                        response["remaining_seconds"] = int(remaining)
                        response["remaining_minutes"] = round(remaining / 60, 1)
                        response["progress_percent"] = min(100, round((elapsed / job.projected_eta) * 100, 1))

                # Add completion data for completed jobs
                if job.status == JobStatus.COMPLETE:
                    # Add output filename for frontend
                    response["filename"] = job.output_filename

                    # Add input filename and file size
                    response["input_filename"] = job.input_filename
                    if job.input_file_size:
                        response["input_file_size"] = job.input_file_size
                        response["input_file_size_formatted"] = format_bytes(job.input_file_size)

                    # Add output file size if available
                    if job.output_file_size:
                        response["output_file_size"] = job.output_file_size
                        response["output_file_size_formatted"] = format_bytes(job.output_file_size)
                    
                    # Add output extension if available
                    if job.output_extension:
                        response["output_extension"] = job.output_extension
                    
                    # Add device profile for frontend display
                    response["device_profile"] = job.device_profile
                    
                    # Add actual duration if available
                    if job.actual_duration:
                        response["actual_duration"] = job.actual_duration
                        response["actual_duration_minutes"] = round(job.actual_duration / 60, 1)
                    
                    # Add download URL for completed jobs
                    # Use session_key as the storage prefix for consistency
                    storage_id = job.session_key
                    minio_output_path = f"{storage_id}/{job_id}/output/{job.output_filename}"
                    # Direct S3 call instead of Celery (fast operation, ~100ms)
                    from utils.storage.s3_storage import S3Storage
                    storage = S3Storage()
                    response["download_url"] = storage.presigned_url(minio_output_path)

                # Only log completion or error status responses
                if response.get('status') in ['COMPLETE', 'ERRORED']:
                    log_with_context(
                        logger, 'info', f'Final status response: {response.get("status")}',
                        job_id=job_id,
                        user_id=request.headers.get("X-Session-Key"),
                        status=response.get('status'),
                        has_download_url=bool(response.get("download_url"))
                    )
                
                return jsonify(response), 200
            else:
                log_with_context(
                    logger, 'warning', 'Status poll for non-existent job',
                    job_id=job_id,
                    user_id=request.headers.get("X-Session-Key")
                )
                return jsonify({"error": "Job not found"}), 404
        except Exception as e:
            log_with_context(
                logger, 'error', f'Error retrieving job status: {str(e)}',
                job_id=job_id,
                user_id=request.headers.get("X-Session-Key"),
                error_type=type(e).__name__
            )
            return jsonify({"error": "Failed to retrieve job status"}), 500
        finally:
            db.close()

    @app.route("/validate", methods=["GET", "HEAD"])
    @require_session_auth
    def validate_session(session_obj=None):
        """Validate session key; returns 204 No Content if valid."""
        return ("", 204)

    @app.route("/download/<job_id>", methods=["GET"])
    @require_session_auth
    def download_file(job_id, session_obj=None):
        """
        Generate presigned download URL and track download.

        OPTIMIZED: Redis-first approach
        - Download counter tracked in Redis
        - Persisted to DB when status changes COMPLETE → DOWNLOADED
        """
        from utils.redis_job_store import RedisJobStore

        # Try Redis first (fast)
        job_data = RedisJobStore.get_job(job_id)

        if not job_data:
            # Fallback to DB for completed jobs that may have been cleaned from Redis
            db = get_db_session()
            try:
                job = db.query(ConversionJob).get(job_id)
                if not job:
                    return jsonify({"error": "Job not found"}), 404

                # Reconstruct job_data dict from DB model
                job_data = {
                    'id': job.id,
                    'status': job.status.value if hasattr(job.status, 'value') else job.status,
                    'session_key': job.session_key,
                    'output_filename': job.output_filename,
                    'download_attempts': job.download_attempts or 0
                }
            finally:
                db.close()

        # Validate job status
        job_status = job_data.get('status')
        if job_status != 'COMPLETE' and job_status != JobStatus.COMPLETE.value:
            return jsonify({"error": "Job not completed"}), 400

        # Get job details
        storage_id = job_data.get('session_key')
        output_filename = job_data.get('output_filename')
        download_attempts = job_data.get('download_attempts', 0)

        minio_output_path = f"{storage_id}/{job_id}/output/{output_filename}"

        log_with_context(
            logger, 'info', 'Generating download link',
            job_id=job_id,
            user_id=storage_id,
            output_path=minio_output_path,
            filename=output_filename,
            download_attempt=download_attempts + 1
        )

        try:
            # Direct S3 call (fast operation, ~100ms)
            from utils.storage.s3_storage import S3Storage
            storage = S3Storage()
            presigned_url = storage.presigned_url(minio_output_path)

            # Increment download counter in Redis
            new_download_count = download_attempts + 1
            RedisJobStore.update_job(job_id, {
                'download_attempts': new_download_count,
                'status': JobStatus.DOWNLOADED.value
            })

            # Persist to DB (status change COMPLETE → DOWNLOADED)
            db = get_db_session()
            try:
                job = db.query(ConversionJob).get(job_id)
                if job:
                    job.download_attempts = new_download_count
                    change_status(job, JobStatus.DOWNLOADED, db, storage_id, {
                        'download_completed': True,
                        'download_attempts': new_download_count,
                        'presigned_url_expires_in': '1 hour'
                    })
            finally:
                db.close()

            log_with_context(
                logger, 'info', 'Download link provided',
                job_id=job_id,
                user_id=storage_id,
                download_attempts=new_download_count,
                presigned_url_expires_in='1 hour'
            )

            return redirect(presigned_url)

        except Exception as e:
            log_with_context(
                logger, 'error', f'Error retrieving download link: {str(e)}',
                job_id=job_id,
                user_id=request.headers.get("X-Session-Key"),
                error_type=type(e).__name__
            )
            return jsonify({"error": "Failed to retrieve download link"}), 500

    @app.route("/api/log", methods=["POST"])
    def receive_frontend_log():
        """Receive logs from frontend"""
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON body provided"}), 400

        # Use enhanced logging with proper context
        level = data.get("level", "INFO").lower()
        message = data.get("message", "")
        job_id = data.get("job_id")
        user_id = data.get("user_id")
        context = data.get("context", {})

        # Sanitize job_id: ensure it's a string or None (not dict or other objects)
        if job_id is not None and not isinstance(job_id, str):
            # If job_id is a dict or other object, try to extract useful info or set to None
            if isinstance(job_id, dict):
                # If it's a dict, maybe it contains error info - add to context
                context["invalid_job_id"] = job_id
                job_id = None
            else:
                job_id = str(job_id)

        # Add source to context
        context["source"] = "frontend"

        log_with_context(
            logger,
            level,
            message,
            job_id=job_id,
            user_id=user_id,
            **context
        )

        return {"status": "logged"}

    @app.route("/api/logs/<job_id>", methods=["GET"])
    @require_session_auth
    def get_job_logs(job_id, session_obj=None):
        """Get logs for a specific job"""
        db = get_db_session()
        try:
            logs = db.query(LogEntry).filter(LogEntry.job_id == job_id).order_by(LogEntry.timestamp.asc()).all()

            result = []
            for log in logs:
                result.append({
                    'id': log.id,
                    'timestamp': log.timestamp.isoformat(),
                    'level': log.level,
                    'message': log.message,
                    'source': log.source,
                    'context': log.context or {}
                })

            return {"logs": result}
        except Exception as e:
            log_with_context(
                logger, 'error', f'Error retrieving logs for job {job_id}: {str(e)}',
                job_id=job_id,
                error_type=type(e).__name__
            )
            return jsonify({"error": "Failed to retrieve logs"}), 500
        finally:
            db.close()

    @app.route("/api/logs", methods=["GET"])
    def get_all_logs():
        """Get recent logs with optional filters"""
        db = get_db_session()
        try:
            # Get query parameters
            level = request.args.get('level')
            source = request.args.get('source')
            limit = int(request.args.get('limit', 100))
            
            query = db.query(LogEntry)
            
            if level:
                query = query.filter(LogEntry.level == level)
            if source:
                query = query.filter(LogEntry.source == source)
            
            logs = query.order_by(LogEntry.timestamp.desc()).limit(limit).all()
            
            result = []
            for log in logs:
                result.append({
                    'id': log.id,
                    'timestamp': log.timestamp.isoformat(),
                    'level': log.level,
                    'message': log.message,
                    'source': log.source,
                    'job_id': log.job_id,
                    'user_id': log.user_id,
                    'context': log.context or {}
                })
            
            return {"logs": result}
        except Exception as e:
            log_with_context(
                logger, 'error', f'Error retrieving logs: {str(e)}',
                error_type=type(e).__name__
            )
            return jsonify({"error": "Failed to retrieve logs"}), 500
        finally:
            db.close()

    # REMOVED: /admin/delete-user/<alias> endpoint - unused by dashboard
    # Streamlit dashboard performs direct SQL DELETE operations for admin tasks
    # Keeping only /api/auth/delete-user for user-initiated account deletion

    @app.route("/jobs/<job_id>/multipart/initiate", methods=["POST"])
    @require_session_auth
    def initiate_multipart_upload(job_id, session_obj=None):
        """
        Initiate S3 multipart upload for a job with batched presigned URL generation.

        Request body:
        {
            "file_size": 12345678,  # Total file size in bytes
            "part_size": 5242880,   # Optional: Part size in bytes (default: 50MB)
            "initial_batch_size": 20  # Optional: Number of URLs to return immediately (default: 20)
        }

        Returns first batch of presigned URLs immediately for fast upload start.
        Frontend can fetch remaining URLs in background using /multipart/get-parts.
        """
        data = request.get_json()
        file_size = data.get("file_size")
        part_size = data.get("part_size", 50 * 1024 * 1024)  # Default 50MB per part
        initial_batch_size = data.get("initial_batch_size", 20)  # Return first 20 URLs immediately

        if not file_size:
            return jsonify({"error": "file_size is required"}), 400

        # Calculate number of parts needed
        num_parts = (file_size + part_size - 1) // part_size  # Ceiling division

        # S3 multipart upload limits: 1-10,000 parts
        if num_parts > 10000:
            return jsonify({
                "error": "File too large for multipart upload",
                "max_file_size": 10000 * part_size,
                "suggested_part_size": (file_size + 9999) // 10000
            }), 400

        session_key = session_obj.session_key if session_obj else None

        # Get job from Redis (fast: <1ms vs 50-100ms DB query)
        from utils.redis_job_store import RedisJobStore
        job = RedisJobStore.get_job(job_id)

        if not job:
            return jsonify({"error": "Job not found"}), 404

        if job.get('session_key') != session_key:
            return jsonify({"error": "Unauthorized"}), 403

        if job.get('status') != 'UPLOADING':
            return jsonify({"error": f"Job is in {job.get('status')} status, expected uploading"}), 400

        # Use s3_key from Redis (already set during job creation)
        s3_key = job.get('s3_key')
        if not s3_key:
            # Fallback: construct from session_key
            storage_id = session_key
            s3_key = f"{storage_id}/{job_id}/input/{job.get('input_filename')}"

        try:
            # Initiate S3 multipart upload directly (no Celery - must be synchronous)
            from utils.storage.s3_storage import S3Storage
            s3_storage = S3Storage()
            upload_id = s3_storage.initiate_multipart_upload(s3_key)

            # OPTIMIZATION: Generate only FIRST BATCH of presigned URLs immediately
            # This reduces initialization time from 15-30s to 2-5s for large files
            import concurrent.futures
            import time

            batch_start = time.time()
            batch_size = min(initial_batch_size, num_parts)
            part_urls = []

            # Use thread pool to parallelize presigned URL generation (10x faster)
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                future_to_part = {
                    executor.submit(
                        s3_storage.generate_multipart_part_url,
                        s3_key,
                        upload_id,
                        part_number
                    ): part_number
                    for part_number in range(1, batch_size + 1)
                }

                for future in concurrent.futures.as_completed(future_to_part):
                    part_number = future_to_part[future]
                    try:
                        url = future.result()
                        part_urls.append({
                            "part_number": part_number,
                            "url": url
                        })
                    except Exception as e:
                        log_with_context(
                            logger, 'error', f'Failed to generate URL for part {part_number}: {str(e)}',
                            job_id=job_id,
                            part_number=part_number
                        )
                        raise

            # Sort by part number
            part_urls.sort(key=lambda x: x['part_number'])
            batch_time = time.time() - batch_start

            # Update job in Redis with multipart upload info
            RedisJobStore.update_job(job_id, {
                's3_upload_id': upload_id,
                's3_key': s3_key,
                's3_parts_total': num_parts
            })

            log_with_context(
                logger, 'info', 'Initiated multipart upload with batched URL generation',
                job_id=job_id,
                user_id=session_key,
                s3_key=s3_key,
                upload_id=upload_id,
                num_parts=num_parts,
                initial_batch_size=batch_size,
                batch_generation_time_ms=int(batch_time * 1000),
                file_size=file_size,
                storage='redis',
                optimization='batched_parallel_generation'
            )

            return jsonify({
                "upload_id": upload_id,
                "s3_key": s3_key,
                "num_parts": num_parts,
                "part_size": part_size,
                "parts": part_urls,
                "has_more_parts": num_parts > batch_size,
                "next_part_number": batch_size + 1 if num_parts > batch_size else None
            }), 200

        except Exception as e:
            log_with_context(
                logger, 'error', f'Failed to initiate multipart upload: {str(e)}',
                job_id=job_id,
                error_type=type(e).__name__
            )
            return jsonify({"error": "Failed to initiate multipart upload"}), 500

    @app.route("/jobs/<job_id>/multipart/get-parts", methods=["POST"])
    @require_session_auth
    def get_multipart_parts_batch(job_id, session_obj=None):
        """
        Get a batch of presigned URLs for multipart upload parts.

        Request body:
        {
            "start_part": 21,  # First part number to fetch
            "batch_size": 20   # Number of URLs to return (default: 20)
        }

        Used by frontend to fetch additional URL batches after initial upload starts.
        This enables progressive upload without waiting for all URLs to be generated.
        """
        data = request.get_json()
        start_part = data.get("start_part")
        batch_size = data.get("batch_size", 20)

        if not start_part or start_part < 1:
            return jsonify({"error": "start_part is required and must be >= 1"}), 400

        try:
            from utils.redis_job_store import RedisJobStore

            session_key = session_obj.session_key if session_obj else None

            # Get job from Redis (UPLOADING jobs are in Redis)
            job = RedisJobStore.get_job(job_id)
            if not job:
                return jsonify({"error": "Job not found"}), 404

            if job.get('session_key') != session_key:
                return jsonify({"error": "Unauthorized"}), 403

            job_status = job.get('status')
            if job_status != 'UPLOADING':
                return jsonify({"error": f"Job is in {job_status} status, expected uploading"}), 400

            s3_upload_id = job.get('s3_upload_id')
            s3_key = job.get('s3_key')
            s3_parts_total = job.get('s3_parts_total')

            if not s3_upload_id or not s3_key:
                return jsonify({"error": "No multipart upload in progress"}), 400

            # Calculate end part (inclusive)
            end_part = min(start_part + batch_size - 1, s3_parts_total)

            # Generate presigned URLs for this batch using parallel execution
            from utils.storage.s3_storage import S3Storage
            import concurrent.futures
            import time

            batch_start = time.time()
            s3_storage = S3Storage()
            part_urls = []

            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                future_to_part = {
                    executor.submit(
                        s3_storage.generate_multipart_part_url,
                        s3_key,
                        s3_upload_id,
                        part_number
                    ): part_number
                    for part_number in range(start_part, end_part + 1)
                }

                for future in concurrent.futures.as_completed(future_to_part):
                    part_number = future_to_part[future]
                    try:
                        url = future.result()
                        part_urls.append({
                            "part_number": part_number,
                            "url": url
                        })
                    except Exception as e:
                        log_with_context(
                            logger, 'error', f'Failed to generate URL for part {part_number}: {str(e)}',
                            job_id=job_id,
                            part_number=part_number
                        )
                        raise

            # Sort by part number
            part_urls.sort(key=lambda x: x['part_number'])
            batch_time = time.time() - batch_start

            log_with_context(
                logger, 'info', 'Generated additional URL batch',
                job_id=job_id,
                user_id=session_key,
                start_part=start_part,
                end_part=end_part,
                batch_size=len(part_urls),
                batch_generation_time_ms=int(batch_time * 1000),
                storage='redis'
            )

            return jsonify({
                "parts": part_urls,
                "start_part": start_part,
                "end_part": end_part,
                "has_more_parts": end_part < s3_parts_total,
                "next_part_number": end_part + 1 if end_part < s3_parts_total else None
            }), 200

        except Exception as e:
            log_with_context(
                logger, 'error', f'Failed to get parts batch: {str(e)}',
                job_id=job_id,
                error_type=type(e).__name__
            )
            return jsonify({"error": "Failed to get parts batch"}), 500

    @app.route("/jobs/<job_id>/multipart/info", methods=["GET"])
    @require_session_auth
    def get_multipart_upload_info(job_id, session_obj=None):
        """
        Get existing multipart upload info for resuming.

        Returns the same format as initiate, but with existing upload_id and parts.
        """
        db = get_db_session()
        try:
            session_key = session_obj.session_key if session_obj else None

            # Get job and verify ownership
            job = db.query(ConversionJob).get(job_id)
            if not job:
                return jsonify({"error": "Job not found"}), 404

            if job.session_key != session_key:
                return jsonify({"error": "Unauthorized"}), 403

            if job.status != JobStatus.UPLOADING:
                return jsonify({"error": f"Job is in {job.status.value} status, expected uploading"}), 400

            if not job.s3_upload_id or not job.s3_key:
                return jsonify({"error": "No existing upload found"}), 404

            # Re-generate presigned URLs for all parts
            from utils.storage.s3_storage import S3Storage
            s3_storage = S3Storage()

            part_urls = []
            for part_number in range(1, job.s3_parts_total + 1):
                url = s3_storage.generate_multipart_part_url(job.s3_key, job.s3_upload_id, part_number)
                part_urls.append({
                    "part_number": part_number,
                    "url": url
                })

            log_with_context(
                logger, 'info', 'Retrieved multipart upload info for resume',
                job_id=job_id,
                user_id=session_key,
                upload_id=job.s3_upload_id,
                parts_completed=job.s3_parts_completed,
                parts_total=job.s3_parts_total
            )

            return jsonify({
                "upload_id": job.s3_upload_id,
                "s3_key": job.s3_key,
                "num_parts": job.s3_parts_total,
                "parts_completed": job.s3_parts_completed,
                "parts": part_urls
            }), 200

        except Exception as e:
            log_with_context(
                logger, 'error', f'Failed to get multipart upload info: {str(e)}',
                job_id=job_id,
                error_type=type(e).__name__
            )
            return jsonify({"error": "Failed to get upload info"}), 500
        finally:
            db.close()

    @app.route("/jobs/<job_id>/multipart/complete-part", methods=["POST"])
    @require_session_auth
    def complete_multipart_part(job_id, session_obj=None):
        """
        Track completion of a single part in the multipart upload.

        REDIS-ONLY IMPLEMENTATION: Stores parts in Redis to eliminate database lock contention.
        Parts are only synced to PostgreSQL during finalization.

        Request body:
        {
            "part_number": 1,
            "etag": "\"abc123...\""
        }

        Returns updated progress.
        """
        data = request.get_json()
        part_number = data.get("part_number")
        etag = data.get("etag")

        if not part_number or not etag:
            return jsonify({"error": "part_number and etag are required"}), 400

        from utils.rate_limiter import redis_client
        from utils.redis_job_store import RedisJobStore
        import json

        session_key = session_obj.session_key if session_obj else None

        # Get job from Redis (fast: <1ms)
        job = RedisJobStore.get_job(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404

        if job.get('session_key') != session_key:
            return jsonify({"error": "Unauthorized"}), 403

        if job.get('status') != 'UPLOADING':
            return jsonify({"error": f"Job is in {job.get('status')} status, expected uploading"}), 400

        total_parts = job.get('s3_parts_total', 0)
        file_size = job.get('file_size', 0)

        # REDIS-ONLY: Store part info (atomic, zero lock contention)
        redis_key = f"multipart_parts:{job_id}"

        try:
            # Store part atomically in Redis hash
            redis_client.hset(redis_key, str(part_number), etag)

            # Get total completed parts count atomically
            parts_count = redis_client.hlen(redis_key)

            # Set TTL (24 hours - cleaned up after finalize/abort)
            redis_client.expire(redis_key, 86400)

            # Calculate progress for response
            upload_progress_bytes = 0
            if total_parts and file_size:
                progress_percent = (parts_count / total_parts) * 100
                upload_progress_bytes = int((progress_percent / 100) * file_size)

            log_with_context(
                logger, 'info', 'Completed multipart part (Redis)',
                job_id=job_id,
                user_id=session_key,
                part_number=part_number,
                completed_parts=parts_count,
                total_parts=total_parts,
                progress_percent=f"{(parts_count / total_parts * 100):.1f}%" if total_parts else "N/A",
                storage='redis'
            )

            # Broadcast progress update via WebSocket
            from utils.websocket import broadcast_job_status
            broadcast_job_status(job_id, {
                'status': 'UPLOADING',
                'upload_progress_bytes': upload_progress_bytes,
                'multipart_progress': {
                    'completed_parts': parts_count,
                    'total_parts': total_parts,
                    'percent': (parts_count / total_parts * 100) if total_parts else 0
                }
            })

            return jsonify({
                "success": True,
                "completed_parts": parts_count,
                "total_parts": total_parts,
                "upload_progress_bytes": upload_progress_bytes
            }), 200

        except Exception as e:
            log_with_context(
                logger, 'error', f'Failed to complete multipart part in Redis: {str(e)}',
                job_id=job_id,
                part_number=part_number,
                error_type=type(e).__name__
            )
            return jsonify({"error": "Failed to complete part"}), 500

    @app.route("/jobs/<job_id>/multipart/finalize", methods=["POST"])
    @require_session_auth
    def finalize_multipart_upload(job_id, session_obj=None):
        """
        Finalize the multipart upload and start job processing.

        This completes the S3 multipart upload by combining all parts.
        Reads part info from Redis (source of truth) and syncs to DB.
        """
        from utils.rate_limiter import redis_client
        from utils.redis_job_store import RedisJobStore

        session_key = session_obj.session_key if session_obj else None

        # Get job from Redis
        job = RedisJobStore.get_job(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404

        if job.get('session_key') != session_key:
            return jsonify({"error": "Unauthorized"}), 403

        if job.get('status') != 'UPLOADING':
            return jsonify({"error": f"Job is in {job.get('status')} status, expected uploading"}), 400

        s3_upload_id = job.get('s3_upload_id')
        s3_key = job.get('s3_key')
        if not s3_upload_id or not s3_key:
            return jsonify({"error": "No multipart upload in progress"}), 400

        try:
            from datetime import datetime

            # REDIS: Read all completed parts (source of truth)
            redis_key = f"multipart_parts:{job_id}"
            parts_dict = redis_client.hgetall(redis_key)

            s3_parts_total = job.get('s3_parts_total', 0)
            file_size = job.get('file_size', 0)

            if not parts_dict:
                return jsonify({
                    "error": "No parts found in Redis",
                    "completed_parts": 0,
                    "total_parts": s3_parts_total
                }), 400

            # Convert Redis hash to parts_info format for S3
            parts_info = [
                {'PartNumber': int(part_num), 'ETag': etag}
                for part_num, etag in parts_dict.items()
            ]

            # Sort by part number (S3 requires this)
            parts_info.sort(key=lambda x: x['PartNumber'])

            # Verify all parts are present
            if len(parts_info) != s3_parts_total:
                return jsonify({
                    "error": "Upload incomplete: Only {} of {} parts were confirmed by the backend. This may happen if the page was refreshed during upload or if there were network errors.".format(
                        len(parts_info), s3_parts_total
                    ),
                    "completed_parts": len(parts_info),
                    "total_parts": s3_parts_total
                }), 400

            # Complete the S3 multipart upload directly (fast operation, ~200ms)
            from utils.storage.s3_storage import S3Storage
            storage = S3Storage()
            response = storage.complete_multipart_upload(s3_key, s3_upload_id, parts_info)

            # Update job in Redis: upload complete, now QUEUED for processing
            RedisJobStore.update_job(job_id, {
                'status': 'QUEUED',
                'upload_progress_bytes': file_size,
                's3_parts_info': parts_info,
                's3_parts_completed': len(parts_info),
                'queued_at': datetime.utcnow()
            })

            log_with_context(
                logger, 'info', '=== MULTIPART UPLOAD COMPLETED - PERSISTING TO DB AND STARTING PROCESSING ===',
                job_id=job_id,
                user_id=session_key,
                s3_key=s3_key,
                upload_id=s3_upload_id,
                total_parts=len(parts_info),
                file_size=file_size,
                storage='redis',
                flow_step='multipart_upload_complete'
            )

            # CRITICAL: Persist to DB now that job is QUEUED (processing will start)
            # Get updated job from Redis with QUEUED status
            job_data = RedisJobStore.get_job(job_id)
            if job_data:
                success = RedisJobStore.persist_to_db(job_id, job_data)
                if success:
                    log_with_context(
                        logger, 'info', 'Job persisted to DB before starting Celery task',
                        job_id=job_id,
                        status='QUEUED'
                    )

                    # Broadcast QUEUED status to WebSocket clients
                    from utils.websocket import broadcast_job_status
                    broadcast_job_status(job_id, {
                        'status': 'QUEUED',
                        'job_id': job_id,
                        'filename': job_data.get('input_filename'),
                        'message': 'Upload complete, queued for processing'
                    })
                else:
                    log_with_context(
                        logger, 'error', 'Failed to persist job to DB - Celery task may fail',
                        job_id=job_id
                    )

            # Clean up Redis parts data (upload complete)
            try:
                redis_client.delete(redis_key)
                log_with_context(
                    logger, 'info', 'Cleaned up Redis multipart data after successful finalize',
                    job_id=job_id,
                    redis_key=redis_key
                )
            except Exception as redis_error:
                # Non-critical - just log it
                log_with_context(
                    logger, 'warning', f'Failed to cleanup Redis data: {str(redis_error)}',
                    job_id=job_id,
                    redis_key=redis_key
                )

            # Remove job from warmup queue (upload complete, workers will process actual job)
            try:
                redis_client.lrem('pending_work', 0, job_id)  # Remove all occurrences
            except Exception:
                pass  # Non-critical, list has TTL anyway

        except Exception as e:
            # Mark job as errored in Redis
            try:
                redis_key = f"multipart_parts:{job_id}"
                final_parts_count = redis_client.hlen(redis_key) if redis_client else 0

                # Update job to ERROR status in Redis
                RedisJobStore.update_job(job_id, {
                    'status': 'ERROR',
                    'error_message': str(e),
                    'error_phase': 'finalize_multipart_upload',
                    'error_type': type(e).__name__,
                    'errored_at': datetime.utcnow(),
                    's3_parts_completed': final_parts_count
                })

                # Persist error to DB (ERROR is terminal state)
                job_data = RedisJobStore.get_job(job_id)
                if job_data:
                    RedisJobStore.persist_to_db(job_id, job_data)

                    # Broadcast ERROR status to WebSocket clients
                    from utils.websocket import broadcast_job_status
                    broadcast_job_status(job_id, {
                        'status': 'ERRORED',
                        'job_id': job_id,
                        'error': str(e),
                        'message': 'Upload failed during finalization'
                    })

                # Clean up Redis parts data
                try:
                    redis_client.delete(redis_key)
                except Exception:
                    pass

                log_with_context(
                    logger, 'error', 'Failed to finalize multipart upload - job marked as ERROR',
                    job_id=job_id,
                    error=str(e),
                    error_type=type(e).__name__,
                    parts_completed=final_parts_count
                )
            except Exception as cleanup_error:
                log_with_context(
                    logger, 'warning', f'Failed to handle error cleanup: {str(cleanup_error)}',
                    job_id=job_id
                )

            return jsonify({"error": "Failed to finalize upload"}), 500

        # Queue task to Celery for processing (file already uploaded to S3)
        try:
            # Job should now be in DB (we persisted it above when status changed to QUEUED)
            # Celery tasks read from DB, so this should work

            # Get fresh job data from Redis for Celery task
            job_data_for_celery = RedisJobStore.get_job(job_id)
            if not job_data_for_celery:
                raise Exception("Job not found in Redis after finalization")

            # Extract storage_id from s3_key (format: {storage_id}/{job_id}/input/{filename})
            storage_id = session_key  # Default
            if job_data_for_celery.get('s3_key'):
                try:
                    storage_id = job_data_for_celery['s3_key'].split('/')[0]
                except:
                    pass

            # Build advanced_options dict from atomized fields
            advanced_options = {}
            option_fields = [
                'manga_style', 'hq', 'two_panel', 'webtoon', 'no_processing',
                'upscale', 'stretch', 'autolevel', 'black_borders', 'white_borders',
                'force_color', 'force_png', 'mozjpeg', 'no_kepub', 'spread_shift',
                'no_rotate', 'rotate_first', 'target_size', 'splitter', 'cropping',
                'custom_width', 'custom_height', 'gamma', 'cropping_power',
                'preserve_margin', 'author', 'title', 'output_format'
            ]
            for field in option_fields:
                if field in job_data_for_celery and job_data_for_celery[field]:
                    advanced_options[field] = job_data_for_celery[field]

            # Queue the Celery task (it will download from S3 and process)
            async_result = celery_app.send_task('mangaconverter.convert_file', kwargs={
                "job_id": job_id,
                "upload_name": job_data_for_celery.get('input_filename'),
                "session_key": session_key,
                "options": {"advanced_options": advanced_options},
                "device_profile": job_data_for_celery.get('device_profile'),
                "alias": storage_id
            })

            # Store task_id in Redis and DB
            RedisJobStore.update_job(job_id, {'celery_task_id': async_result.id})

            # Also update in DB (job should be there from persistence above)
            db2 = get_db_session()
            try:
                job_to_update = db2.query(ConversionJob).get(job_id)
                if job_to_update:
                    job_to_update.celery_task_id = async_result.id
                    db2.commit()
            finally:
                db2.close()

            log_with_context(
                logger, 'info', '=== JOB QUEUED IN CELERY (MULTIPART) ===',
                job_id=job_id,
                user_id=session_key,
                task_id=async_result.id,
                flow_step='celery_task_queued_multipart'
            )

        except Exception as celery_error:
            log_with_context(
                logger, 'error', f'Failed to queue Celery task after multipart upload: {str(celery_error)}',
                job_id=job_id,
                user_id=session_key,
                error_type=type(celery_error).__name__
            )
            return jsonify({"error": "Failed to queue task"}), 500

        return jsonify({
            "success": True,
            "message": "Upload finalized, processing started",
            "status": JobStatus.QUEUED.value
        }), 200

    @app.route("/jobs/<job_id>/upload-progress", methods=["POST"])
    @require_session_auth
    def save_upload_progress(job_id, session_obj=None):
        """
        Save upload progress to Redis for refresh resilience.

        Called by the frontend after each multipart chunk is uploaded.
        Allows progress to be restored after page refresh.
        """
        db = get_db_session()
        try:
            session_key = session_obj.session_key if session_obj else None

            # Get job and verify ownership
            job = db.query(ConversionJob).get(job_id)
            if not job:
                return jsonify({"error": "Job not found"}), 404

            if job.session_key != session_key:
                return jsonify({"error": "Unauthorized"}), 403

            # Get progress data from request
            data = request.get_json()
            parts_completed = data.get('parts_completed', 0)
            parts_total = data.get('parts_total', 100)
            uploaded_bytes = data.get('uploaded_bytes', 0)
            total_bytes = data.get('total_bytes', 0)

            # Save upload progress to dedicated Redis key (independent of queue sync)
            from utils.rate_limiter import redis_client
            import json

            # Store progress in a dedicated key for this job
            progress_key = f"upload_progress:{job_id}"
            progress_data = {
                'parts_completed': parts_completed,
                'parts_total': parts_total,
                'uploaded_bytes': uploaded_bytes,
                'total_bytes': total_bytes,
            }

            # Save to dedicated progress key (24h TTL)
            redis_client.setex(progress_key, 86400, json.dumps(progress_data))

            log_with_context(
                logger, 'info', 'Upload progress saved to Redis',
                job_id=job_id,
                user_id=session_key,
                parts_completed=parts_completed,
                parts_total=parts_total,
                percentage=round((parts_completed / parts_total * 100) if parts_total > 0 else 0, 1),
                progress_key=progress_key
            )

            return jsonify({
                "success": True,
                "parts_completed": parts_completed,
                "parts_total": parts_total
            }), 200

        except Exception as e:
            log_with_context(
                logger, 'error', f'Failed to save upload progress: {str(e)}',
                job_id=job_id,
                error_type=type(e).__name__
            )
            return jsonify({"error": "Failed to save progress"}), 500
        finally:
            db.close()

    @app.route("/jobs/<job_id>/multipart/abort", methods=["POST"])
    @require_session_auth
    def abort_multipart_upload(job_id, session_obj=None):
        """
        Abort the multipart upload and cleanup S3 parts and Redis data.
        """
        from utils.rate_limiter import redis_client
        from utils.redis_job_store import RedisJobStore
        from datetime import datetime

        session_key = session_obj.session_key if session_obj else None

        # Get job from Redis
        job = RedisJobStore.get_job(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404

        if job.get('session_key') != session_key:
            return jsonify({"error": "Unauthorized"}), 403

        s3_upload_id = job.get('s3_upload_id')
        s3_key = job.get('s3_key')
        if not s3_upload_id or not s3_key:
            return jsonify({"error": "No multipart upload in progress"}), 400

        try:
            # Abort the S3 multipart upload directly (fast operation, ~100ms)
            from utils.storage.s3_storage import S3Storage
            storage = S3Storage()
            storage.abort_multipart_upload(s3_key, s3_upload_id)

            # Capture final upload progress for analytics
            redis_key = f"multipart_parts:{job_id}"
            final_parts_count = 0
            try:
                final_parts_count = redis_client.hlen(redis_key) if redis_client else 0

                s3_parts_total = job.get('s3_parts_total', 0)
                file_size = job.get('file_size', 0)

                if final_parts_count > 0 and s3_parts_total:
                    progress_percent = (final_parts_count / s3_parts_total) * 100
                    final_progress_bytes = int((progress_percent / 100) * file_size)

                    log_with_context(
                        logger, 'info', 'Captured upload progress before abort',
                        job_id=job_id,
                        parts_completed=final_parts_count,
                        parts_total=s3_parts_total,
                        progress_percent=round(progress_percent, 1),
                        progress_bytes=final_progress_bytes
                    )
                else:
                    final_progress_bytes = 0
            except Exception as progress_error:
                log_with_context(
                    logger, 'warning', f'Failed to capture upload progress: {str(progress_error)}',
                    job_id=job_id
                )
                final_progress_bytes = 0

            # Clean up Redis parts data
            try:
                deleted_count = redis_client.delete(redis_key)
                log_with_context(
                    logger, 'info', 'Cleaned up Redis multipart data after abort',
                    job_id=job_id,
                    redis_key=redis_key,
                    keys_deleted=deleted_count
                )
            except Exception as redis_error:
                log_with_context(
                    logger, 'warning', f'Failed to cleanup Redis data: {str(redis_error)}',
                    job_id=job_id,
                    redis_key=redis_key
                )

            # Remove job from warmup queue (upload cancelled)
            try:
                redis_client.lrem('pending_work', 0, job_id)  # Remove all occurrences
            except Exception:
                pass  # Non-critical, list has TTL anyway

            # Update job to CANCELLED in Redis
            RedisJobStore.update_job(job_id, {
                'status': 'CANCELLED',
                'cancelled_at': datetime.utcnow(),
                's3_parts_completed': final_parts_count,
                'upload_progress_bytes': final_progress_bytes,
                's3_upload_id': None,  # Clear multipart identifiers
                's3_parts_total': None,
                's3_parts_info': None
            })

            # Persist to DB (CANCELLED is terminal state)
            job_data = RedisJobStore.get_job(job_id)
            if job_data:
                RedisJobStore.persist_to_db(job_id, job_data)

                # Broadcast CANCELLED status to WebSocket clients
                from utils.websocket import broadcast_job_status
                broadcast_job_status(job_id, {
                    'status': 'CANCELLED',
                    'job_id': job_id,
                    'message': 'Multipart upload aborted'
                })

            log_with_context(
                logger, 'info', 'Aborted multipart upload - job marked CANCELLED',
                job_id=job_id,
                user_id=session_key,
                storage='redis'
            )

            return jsonify({
                "success": True,
                "message": "Multipart upload aborted"
            }), 200

        except Exception as e:
            log_with_context(
                logger, 'error', f'Failed to abort multipart upload: {str(e)}',
                job_id=job_id,
                error_type=type(e).__name__
            )
            return jsonify({"error": "Failed to abort upload"}), 500

    @app.route("/api/queue/sync", methods=["POST", "GET"])
    @require_session_auth
    def sync_queue(session_obj=None):
        """
        Redis-based queue sync for refresh resilience.

        POST: Save queue state to Redis
        GET: Retrieve queue state from Redis

        Queue data is stored with 24-hour TTL and scoped to session.
        This enables:
        - Queue persistence across page refreshes
        - Cross-tab sync (all tabs see same queue)
        - Upload resumption (stores S3 multipart state)
        """
        from utils.rate_limiter import redis_client

        session_key = request.headers.get('X-Session-Key')
        redis_key = f"queue:{session_key}"

        if not redis_client:
            # Redis unavailable - return error for POST, empty for GET
            if request.method == 'POST':
                return jsonify({"error": "Queue sync unavailable"}), 503
            else:
                return jsonify({"jobs": []}), 200

        try:
            if request.method == 'POST':
                # Save queue state to Redis
                queue_data = request.json.get('jobs', [])

                if queue_data:
                    # Store with 24-hour TTL (same as localStorage)
                    redis_client.setex(
                        redis_key,
                        86400,  # 24 hours in seconds
                        json.dumps(queue_data)
                    )

                    log_with_context(
                        logger, 'debug', f'Queue synced to Redis ({len(queue_data)} jobs)',
                        user_id=session_key,
                        job_count=len(queue_data)
                    )
                else:
                    # Empty queue - delete Redis key
                    redis_client.delete(redis_key)

                    log_with_context(
                        logger, 'debug', 'Queue cleared from Redis',
                        user_id=session_key
                    )

                return jsonify({"status": "synced", "job_count": len(queue_data)}), 200

            else:  # GET
                # Retrieve queue state from Redis
                data = redis_client.get(redis_key)

                if data:
                    jobs = json.loads(data)

                    # Enrich each job with its upload progress from dedicated key
                    for job in jobs:
                        job_id = job.get('jobId')
                        if job_id and job.get('status') == 'UPLOADING':
                            progress_key = f"upload_progress:{job_id}"
                            progress_data = redis_client.get(progress_key)
                            if progress_data:
                                job['uploadState'] = json.loads(progress_data)
                                log_with_context(
                                    logger, 'debug', 'Loaded upload progress for job',
                                    job_id=job_id,
                                    progress=job['uploadState']
                                )

                    log_with_context(
                        logger, 'debug', f'Queue loaded from Redis ({len(jobs)} jobs)',
                        user_id=session_key,
                        job_count=len(jobs)
                    )
                    return jsonify({"jobs": jobs}), 200
                else:
                    return jsonify({"jobs": []}), 200

        except json.JSONDecodeError as e:
            log_with_context(
                logger, 'error', f'Invalid JSON in queue sync: {str(e)}',
                user_id=session_key,
                error_type='JSONDecodeError'
            )
            return jsonify({"error": "Invalid queue data"}), 400

        except Exception as e:
            log_with_context(
                logger, 'error', f'Queue sync failed: {str(e)}',
                user_id=session_key,
                error_type=type(e).__name__
            )

            if request.method == 'POST':
                return jsonify({"error": "Failed to sync queue"}), 500
            else:
                # On GET error, return empty queue (fail gracefully)
                return jsonify({"jobs": []}), 200

    @app.route("/api/queue/status", methods=["GET"])
    @require_session_auth
    def get_queue_status(session_obj=None):
        """
        Get complete queue status for the current session.

        Returns all active jobs (UPLOADING, QUEUED, PROCESSING) with full state including:
        - Job status
        - Upload progress (for multipart uploads)
        - Processing progress (ETA, elapsed time)
        - Download URLs (for completed jobs)

        This endpoint is designed for polling (1-2 second intervals) to replace WebSocket updates.
        """
        session_key = request.headers.get('X-Session-Key')
        if not session_key:
            return jsonify({"error": "No session key provided"}), 401

        db = get_db_session()
        try:
            from database.models import format_bytes
            from utils.rate_limiter import redis_client

            # Force fresh data from database by closing and reopening connection
            # This ensures we don't get stale data from SQLAlchemy's session cache
            db.close()
            db = get_db_session()

            # Get jobs from Redis (active uploads) + DB (processing/complete)
            # UPLOADING and QUEUED jobs are in Redis
            # PROCESSING and COMPLETE jobs are in DB
            from utils.redis_job_store import RedisJobStore

            jobs_data = []

            # 1. Get UPLOADING/QUEUED jobs from Redis
            redis_job_ids = RedisJobStore.get_session_jobs(session_key)
            for job_id in redis_job_ids:
                redis_job = RedisJobStore.get_job(job_id)
                if not redis_job:
                    continue

                status = redis_job.get('status')
                if status in ['UPLOADING', 'QUEUED']:  # Active statuses in Redis
                    job_data = {
                        'job_id': job_id,
                        'filename': redis_job.get('input_filename'),
                        'status': status,
                        'device_profile': redis_job.get('device_profile'),
                        'file_size': redis_job.get('file_size'),
                    }

                    # Add download speed for QUEUED jobs (for simulating Reading File progress)
                    if status == 'QUEUED':
                        # Worker download speed in Mbps (measured dynamically)
                        from utils.network_speed import get_download_speed_mbps
                        job_data['worker_download_speed_mbps'] = get_download_speed_mbps()

                    # Add upload progress for UPLOADING jobs
                    if status == 'UPLOADING':
                        redis_key = f"multipart_parts:{job_id}"
                        parts_count = redis_client.hlen(redis_key) if redis_client else 0
                        s3_parts_total = redis_job.get('s3_parts_total', 0)

                        if parts_count > 0 and s3_parts_total:
                            job_data['upload_progress'] = {
                                'completed_parts': parts_count,
                                'total_parts': s3_parts_total,
                                'uploaded_bytes': redis_job.get('upload_progress_bytes', 0),
                                'total_bytes': redis_job.get('file_size', 0),
                                'percentage': round((parts_count / s3_parts_total) * 100, 1)
                            }
                        else:
                            job_data['upload_progress'] = {
                                'uploaded_bytes': redis_job.get('upload_progress_bytes', 0),
                                'total_bytes': redis_job.get('file_size', 0),
                                'percentage': 0
                            }

                    jobs_data.append(job_data)

            # 2. Get PROCESSING/COMPLETE jobs from DB
            db_statuses = [JobStatus.PROCESSING, JobStatus.COMPLETE]
            db_jobs = db.query(ConversionJob).filter(
                ConversionJob.session_key == session_key,
                ConversionJob.status.in_(db_statuses),
                ConversionJob.dismissed_at.is_(None)
            ).order_by(ConversionJob.created_at.asc()).all()

            for job in db_jobs:
                job_data = {
                    'job_id': job.id,
                    'filename': job.input_filename,
                    'status': job.status.value,
                    'device_profile': job.device_profile,
                    'file_size': job.input_file_size,
                }

                # Add processing progress for PROCESSING jobs
                if job.status == JobStatus.PROCESSING:
                    # Use processing_at (when processing started) instead of created_at
                    if job.processing_at and job.projected_eta:
                        elapsed = (datetime.utcnow() - job.processing_at).total_seconds()
                        remaining = max(0, job.projected_eta - elapsed)
                        progress_percent = min(100, round((elapsed / job.projected_eta) * 100, 1))

                        job_data['processing_progress'] = {
                            'elapsed_seconds': int(elapsed),
                            'remaining_seconds': int(remaining),
                            'projected_eta': job.projected_eta,
                            'progress_percent': progress_percent
                        }

                # Add download info for COMPLETE jobs
                if job.status == JobStatus.COMPLETE:
                    if job.output_filename:
                        job_data['output_filename'] = job.output_filename
                        job_data['output_file_size'] = job.output_file_size
                        job_data['download_url'] = f'/jobs/{job.id}/download'

                jobs_data.append(job_data)

            return jsonify({
                "jobs": jobs_data,
                "total": len(jobs_data),
                "timestamp": datetime.utcnow().isoformat()
            }), 200

        except Exception as e:
            log_with_context(
                logger, 'error', f'Error getting queue status: {str(e)}',
                user_id=session_key,
                error_type=type(e).__name__
            )
            return jsonify({"error": "Failed to get queue status"}), 500
        finally:
            db.close()

    @app.route("/api/user/downloads", methods=["GET"])
    @require_session_auth
    def get_user_downloads(session_obj=None):
        """
        Get all completed downloads for the authenticated user across all their sessions.

        Returns all COMPLETE jobs from all sessions associated with the user's Clerk ID.
        This aggregates downloads from all devices/browsers the user has used.

        Query params:
        - limit: Max number of downloads to return (default: 100)
        - offset: Pagination offset (default: 0)
        """
        from database import User, Session as SessionModel

        # Must be authenticated user (not anonymous session)
        if not session_obj or not session_obj.user_id:
            return jsonify({"error": "Authentication required. Please sign in to view your downloads."}), 401

        db = get_db_session()
        try:
            from database.models import format_bytes
            from utils.storage.s3_storage import S3Storage

            # Get pagination params
            limit = request.args.get('limit', 100, type=int)
            offset = request.args.get('offset', 0, type=int)

            # Validate pagination
            if limit > 500:
                limit = 500  # Cap at 500 to prevent abuse
            if offset < 0:
                offset = 0

            # Debug: Log user sessions
            user_sessions = db.query(SessionModel).filter(
                SessionModel.user_id == session_obj.user_id
            ).all()
            logger.info(f"[Downloads] User {session_obj.user_id} has {len(user_sessions)} session(s): {[s.session_key for s in user_sessions]}")

            # Query all COMPLETE and DOWNLOADED jobs across all user's sessions
            # Join: ConversionJob -> Session -> User
            jobs = db.query(ConversionJob).join(
                SessionModel, ConversionJob.session_key == SessionModel.session_key
            ).filter(
                SessionModel.user_id == session_obj.user_id,
                ConversionJob.status.in_([JobStatus.COMPLETE, JobStatus.DOWNLOADED])
                # Show all jobs regardless of dismissal status
            ).order_by(
                ConversionJob.completed_at.desc()  # Most recent first
            ).limit(limit).offset(offset).all()

            logger.info(f"[Downloads] Found {len(jobs)} COMPLETE/DOWNLOADED jobs for user {session_obj.user_id}")

            # Get total count for pagination
            total_count = db.query(ConversionJob).join(
                SessionModel, ConversionJob.session_key == SessionModel.session_key
            ).filter(
                SessionModel.user_id == session_obj.user_id,
                ConversionJob.status.in_([JobStatus.COMPLETE, JobStatus.DOWNLOADED])
            ).count()

            storage = S3Storage()
            downloads_data = []
            skipped_count = 0

            for job in jobs:
                try:
                    # Construct S3 path for output file (standardized to session_key prefix)
                    # Format: {session_key}/{job_id}/output/{output_filename}
                    s3_output_path = f"{job.session_key}/{job.id}/output/{job.output_filename}"

                    # Check if file exists in storage bucket before including it
                    if not storage.exists(s3_output_path):
                        logger.warning(f"[Downloads] Skipping job {job.id}: file {s3_output_path} not found in storage")
                        skipped_count += 1
                        continue

                    # Generate presigned download URL
                    download_url = storage.presigned_url(
                        s3_output_path,
                        expires=604800  # 7 days
                    )

                    download_data = {
                        'job_id': job.id,
                        'original_filename': job.input_filename,
                        'converted_filename': job.output_filename,
                        'device_profile': job.device_profile,
                        'input_file_size': job.input_file_size,
                        'output_file_size': job.output_file_size,
                        'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                        'actual_duration': job.actual_duration,
                        'download_url': download_url,
                        'download_attempts': job.download_attempts,
                        # Session info for context
                        'session_alias': job.session.alias if job.session else None,
                        'session_device': {
                            'browser': job.session.browser_family if job.session else None,
                            'os': job.session.os_family if job.session else None,
                            'device': job.session.device_family if job.session else None,
                        } if job.session else None,
                    }

                    downloads_data.append(download_data)

                except Exception as e:
                    # If presigned URL or file check fails, log but continue with other downloads
                    logger.error(f"Failed to process download for job {job.id}: {e}")
                    skipped_count += 1
                    continue

            log_with_context(
                logger, 'info', f'User downloads fetched: {len(downloads_data)} of {total_count} total ({skipped_count} skipped - file not in storage)',
                user_id=session_obj.user.clerk_user_id if session_obj.user else None,
                downloads_count=len(downloads_data),
                total_count=total_count,
                skipped_count=skipped_count
            )

            return jsonify({
                "downloads": downloads_data,
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + len(downloads_data)) < total_count,
                "timestamp": datetime.utcnow().isoformat()
            }), 200

        except Exception as e:
            log_with_context(
                logger, 'error', f'Error fetching user downloads: {str(e)}',
                user_id=session_obj.user.clerk_user_id if (session_obj and session_obj.user) else None,
                error_type=type(e).__name__
            )
            return jsonify({"error": "Failed to fetch downloads"}), 500
        finally:
            db.close()
