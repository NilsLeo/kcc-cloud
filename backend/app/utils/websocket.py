"""
WebSocket server for real-time job status updates
Replaces HTTP polling with push-based notifications
"""
import logging
try:
    from flask_socketio import SocketIO, emit, join_room, leave_room
    from flask import request
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    SocketIO = None
    emit = None
    join_room = None
    leave_room = None
    request = None

logger = logging.getLogger(__name__)

# Initialize SocketIO (will be configured with app in app.py)
socketio = None

# Track active subscriptions: {job_id: [sid1, sid2, ...]}
active_subscriptions = {}


def _inject_completed_at(jobs):
    """Ensure COMPLETE jobs include completed_at by backfilling from DB if missing."""
    try:
        # Collect job IDs missing completed_at
        missing_ids = [j.get('job_id') for j in jobs if j.get('status') == 'COMPLETE' and not j.get('completed_at')]
        if not missing_ids:
            return jobs

        from database import get_db_session, ConversionJob
        db = get_db_session()
        try:
            rows = db.query(ConversionJob.id, ConversionJob.completed_at).filter(ConversionJob.id.in_(missing_ids)).all()
            completed_map = {row[0]: row[1].isoformat() if getattr(row[1], 'isoformat', None) else str(row[1]) for row in rows if row[1]}
            if completed_map:
                for j in jobs:
                    jid = j.get('job_id')
                    if j.get('status') == 'COMPLETE' and not j.get('completed_at') and jid in completed_map:
                        j['completed_at'] = completed_map[jid]
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"[_inject_completed_at] Failed to backfill completed_at: {e}")
    return jobs


def init_socketio(app):
    """Initialize SocketIO with the Flask app"""
    import os
    global socketio

    if not SOCKETIO_AVAILABLE:
        logger.warning("Flask-SocketIO not available - WebSocket support disabled")
        return None

    # Use Redis as message queue for cross-container communication
    redis_url = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')

    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode='eventlet',
        logger=True,  # Enable logging to debug Redis message queue
        engineio_logger=True,  # Enable Engine.IO logging
        ping_timeout=60,
        ping_interval=25,
        message_queue=redis_url  # Enable Redis pubsub for cross-container broadcasts
    )

    # Register event handlers
    register_socket_handlers(app)

    logger.info(f"WebSocket server initialized with Redis message queue: {redis_url}")
    return socketio


def register_socket_handlers(app):
    """Register all WebSocket event handlers"""

    if not SOCKETIO_AVAILABLE or not socketio:
        return

    @socketio.on('connect')
    def handle_connect():
        """Client connected to WebSocket"""
        logger.info(f"WebSocket client connected: {request.sid}")
        emit('connected', {'message': 'WebSocket connected successfully'})

    @socketio.on('disconnect')
    def handle_disconnect():
        """Client disconnected - cleanup subscriptions and mark abandoned jobs"""
        from database import create_session_with_retry, ConversionJob
        from utils.enums.job_status import JobStatus
        from utils.routes import change_status
        from datetime import datetime
        import threading

        logger.info(f"WebSocket client disconnected: {request.sid}")

        # Track jobs that lost all subscribers
        jobs_to_check = []

        # Remove this client from all job subscriptions
        for job_id in list(active_subscriptions.keys()):
            if request.sid in active_subscriptions[job_id]:
                active_subscriptions[job_id].remove(request.sid)
                logger.info(f"Removed {request.sid} from job {job_id} subscriptions")

                # If this was the last subscriber, schedule abandonment check
                if not active_subscriptions[job_id]:
                    jobs_to_check.append(job_id)
                    del active_subscriptions[job_id]

        # For each job that lost all subscribers, wait 1 minute then check for abandonment
        # This grace period allows for reconnects (network hiccups, page refresh, browser restarts)
        for job_id in jobs_to_check:
            def abandon_after_grace_period(job_id_to_check):
                """Wait 1 minute, then abandon if still no subscribers"""
                import time
                time.sleep(60)  # 1 minute grace period

                # Check if job was re-subscribed during grace period
                if job_id_to_check in active_subscriptions and len(active_subscriptions[job_id_to_check]) > 0:
                    logger.info(f"Job {job_id_to_check} was re-subscribed during grace period, NOT abandoning")
                    return

                # No subscribers after grace period - mark as abandoned
                with app.app_context():
                    db = create_session_with_retry()
                    try:
                        job = db.query(ConversionJob).filter_by(id=job_id_to_check).first()

                        if not job:
                            logger.warning(f"Job {job_id_to_check} not found for abandonment")
                            return

                        # Only abandon active jobs
                        if job.status in [JobStatus.QUEUED, JobStatus.UPLOADING, JobStatus.PROCESSING]:
                            logger.info(f"Abandoning job {job_id_to_check} - all WebSocket clients disconnected")

                            # Revoke Celery task if it's queued (not yet started)
                            if job.celery_task_id and job.status == JobStatus.QUEUED:
                                try:
                                    from celery_config import celery_app
                                    celery_app.control.revoke(job.celery_task_id, terminate=False)
                                    logger.info(f"Revoked Celery task {job.celery_task_id} for abandoned job {job_id_to_check}")
                                except Exception as revoke_error:
                                    logger.error(f"Failed to revoke Celery task {job.celery_task_id}: {revoke_error}")

                            change_status(job, JobStatus.ABANDONED, db, None, {
                                'abandonment_reason': 'websocket_disconnect',
                                'last_subscriber_sid': 'N/A', # No request context here
                                'abandoned_at': datetime.utcnow().isoformat()
                            })
                            db.commit()

                            # Broadcast abandonment status to any new subscribers
                            broadcast_job_status(job_id_to_check, {
                                'status': 'ABANDONED',
                                'message': 'Job abandoned due to client disconnect'
                            })
                        else:
                            logger.info(f"Job {job_id_to_check} in terminal status {job.status.value}, not abandoning")

                    except Exception as e:
                        logger.error(f"Error abandoning job {job_id_to_check}: {e}")
                        db.rollback()
                    finally:
                        db.close()

            # Start grace period timer in background thread
            thread = threading.Thread(target=abandon_after_grace_period, args=(job_id,))
            thread.daemon = True
            thread.start()
            logger.info(f"Started 1-minute grace period for job {job_id} abandonment check")

    @socketio.on('subscribe_job')
    def handle_subscribe_job(data):
        """
        Client subscribes to job updates
        Expected data: {'job_id': 'some-job-id'}
        """
        from database import create_session_with_retry, ConversionJob

        job_id = data.get('job_id')

        if not job_id:
            emit('error', {'message': 'job_id required'})
            logger.warning(f"Subscribe attempt without job_id from {request.sid}")
            return

        # Verify job exists
        db = create_session_with_retry()
        try:
            job = db.query(ConversionJob).filter(ConversionJob.id == job_id).first()

            if not job:
                emit('error', {'message': f'Job {job_id} not found'})
                logger.warning(f"Subscribe attempt for non-existent job {job_id} from {request.sid}")
                return

            # Add client to room for this job
            room = f"job-{job_id}"
            join_room(room)

            # Track subscription
            if job_id not in active_subscriptions:
                active_subscriptions[job_id] = []

            if request.sid not in active_subscriptions[job_id]:
                active_subscriptions[job_id].append(request.sid)

            from database.models import format_bytes

            # Send current status immediately
            upload_progress = getattr(job, 'upload_progress_bytes', 0)
            job_data = {
                'job_id': job_id,
                'status': job.status.value if hasattr(job.status, 'value') else str(job.status),
                'upload_progress_bytes': upload_progress,
                'upload_progress_formatted': format_bytes(upload_progress) if upload_progress else None,
                'projected_eta': job.projected_eta,
            }
            # Add dismissal flag
            try:
                job_data['is_dismissed'] = True if getattr(job, 'dismissed_at', None) else False
                if getattr(job, 'dismissed_at', None):
                    try:
                        job_data['dismissed_at'] = job.dismissed_at.isoformat()
                    except Exception:
                        job_data['dismissed_at'] = str(job.dismissed_at)
            except Exception:
                pass

            # Do not rewrite PROCESSING here; callers must ensure ETA is set before broadcasting

            # Add additional data based on status
            if hasattr(job, 'created_at') and job.created_at:
                from datetime import datetime
                elapsed = (datetime.utcnow() - job.created_at).total_seconds()
                job_data['elapsed_seconds'] = int(elapsed)

                if job.projected_eta and job.projected_eta > 0:
                    remaining = max(0, job.projected_eta - elapsed)
                    job_data['remaining_seconds'] = int(remaining)
                    job_data['progress_percent'] = min(100, int((elapsed / job.projected_eta) * 100))

            # Add download info if complete
            if str(job.status) == 'COMPLETE' or (hasattr(job.status, 'value') and job.status.value == 'COMPLETE'):
                if job.output_filename:
                    job_data['output_filename'] = job.output_filename
                if hasattr(job, 'output_file_size') and job.output_file_size:
                    job_data['output_file_size'] = job.output_file_size
                if hasattr(job, 'input_filename') and job.input_filename:
                    job_data['input_filename'] = job.input_filename
                if hasattr(job, 'input_file_size') and job.input_file_size:
                    job_data['input_file_size'] = job.input_file_size
                if hasattr(job, 'actual_duration') and job.actual_duration:
                    job_data['actual_duration'] = job.actual_duration

                # Generate download URL
                try:
                    from utils.storage.s3_storage import S3Storage
                    storage = S3Storage()
                    # Construct full S3 path: session_key/job_id/output/filename
                    s3_key = f"{job.session_key}/{job_id}/output/{job.output_filename}"
                    download_url = storage.presigned_url(
                        s3_key,
                        expires=604800  # 7 days
                    )
                    job_data['download_url'] = download_url
                except Exception as e:
                    logger.error(f"Failed to generate download URL for job {job_id}: {e}")

            emit('job_status', job_data)

            logger.info(f"Client {request.sid} subscribed to job {job_id}, sent initial status: {job_data['status']}")

        except Exception as e:
            logger.error(f"Error in subscribe_job for {job_id}: {e}")
            emit('error', {'message': f'Failed to subscribe: {str(e)}'})
        finally:
            db.close()

    @socketio.on('subscribe_session')
    def handle_subscribe_session(data):
        """
        Client subscribes to all jobs in their session
        Expected data: {'session_key': 'some-session-key'}
        """
        from utils.redis_job_store import get_active_jobs_for_session
        from datetime import datetime
        from database import create_session_with_retry
        from database.utils import update_session_usage

        session_key = data.get('session_key')

        if not session_key:
            emit('error', {'message': 'session_key required'})
            logger.warning(f"Subscribe session attempt without session_key from {request.sid}")
            return

        # OPTIMIZED: Track session activity in Redis (instant, no DB)
        # Periodic background task syncs to DB every 5 minutes
        try:
            from datetime import datetime
            import redis
            redis_client = redis.from_url('redis://redis:6379/0')
            redis_key = f"session:activity:{session_key}"
            redis_client.set(redis_key, datetime.utcnow().isoformat(), ex=86400)  # 24h TTL
            logger.debug(f"[WebSocket] Tracked session activity in Redis for {session_key[:8]}")
        except Exception as e:
            logger.warning(f"Failed to track session activity in Redis for {session_key[:8]}: {e}")

        # Add client to room for this session
        room = f"session-{session_key}"
        join_room(room)

        logger.info(f"Client {request.sid} subscribed to session {session_key[:8]}...")

        # Send current state immediately
        try:
            jobs = get_active_jobs_for_session(session_key)
            # Safety filter: exclude any dismissed jobs from session payload
            try:
                jobs = [j for j in jobs if not j.get('dismissed_at')]
            except Exception:
                pass
            # Force-inject completed_at for COMPLETE jobs if missing
            jobs = _inject_completed_at(jobs)
            emit('session_update', {
                'jobs': jobs,
                'total': len(jobs),
                'timestamp': datetime.utcnow().isoformat()
            })
            logger.info(f"Sent initial session status to {request.sid}: {len(jobs)} jobs")
        except Exception as e:
            logger.error(f"Error fetching session jobs for {session_key[:8]}: {e}")
            emit('error', {'message': f'Failed to fetch session jobs: {str(e)}'})

    @socketio.on('request_session_status')
    def handle_request_session_status(data):
        """
        Client requests immediate session status update (manual refresh)
        Expected data: {'session_key': 'some-session-key'}
        """
        from utils.redis_job_store import get_active_jobs_for_session
        from datetime import datetime
        from database import create_session_with_retry
        from database.utils import update_session_usage

        session_key = data.get('session_key')

        if not session_key:
            emit('error', {'message': 'session_key required'})
            return

        # OPTIMIZED: Track session activity in Redis (instant, no DB)
        # Periodic background task syncs to DB every 5 minutes
        try:
            from datetime import datetime
            import redis
            redis_client = redis.from_url('redis://redis:6379/0')
            redis_key = f"session:activity:{session_key}"
            redis_client.set(redis_key, datetime.utcnow().isoformat(), ex=86400)  # 24h TTL
            logger.debug(f"[WebSocket] Tracked session activity in Redis for {session_key[:8]}")
        except Exception as e:
            logger.warning(f"Failed to track session activity in Redis for {session_key[:8]}: {e}")

        try:
            jobs = get_active_jobs_for_session(session_key)
            try:
                jobs = [j for j in jobs if not j.get('dismissed_at')]
            except Exception:
                pass
            # Force-inject completed_at for COMPLETE jobs if missing
            jobs = _inject_completed_at(jobs)
            emit('session_update', {
                'jobs': jobs,
                'total': len(jobs),
                'timestamp': datetime.utcnow().isoformat()
            })
            logger.info(f"Sent manual refresh to {request.sid}: {len(jobs)} jobs")
        except Exception as e:
            logger.error(f"Error in manual refresh for {session_key[:8]}: {e}")
            emit('error', {'message': f'Failed to refresh: {str(e)}'})

    @socketio.on('unsubscribe_job')
    def handle_unsubscribe_job(data):
        """
        Client unsubscribes from job updates
        Expected data: {'job_id': 'some-job-id'}
        """
        job_id = data.get('job_id')

        if not job_id:
            return

        room = f"job-{job_id}"
        leave_room(room)

        # Remove from tracking
        if job_id in active_subscriptions and request.sid in active_subscriptions[job_id]:
            active_subscriptions[job_id].remove(request.sid)

            # Clean up empty subscription lists
            if not active_subscriptions[job_id]:
                del active_subscriptions[job_id]

        logger.info(f"Client {request.sid} unsubscribed from job {job_id}")

    @socketio.on('upload_progress')
    def handle_upload_progress(data):
        """
        Client sends real-time upload progress updates
        Expected data: {'job_id': 'some-job-id', 'bytes_uploaded': 123456}

        REDIS-ONLY: Progress updates are stored in Redis during upload.
        Database is only updated when status changes (UPLOADING -> QUEUED).
        """
        from database.models import format_bytes
        from utils.redis_job_store import RedisJobStore

        job_id = data.get('job_id')
        bytes_uploaded = data.get('bytes_uploaded', 0)

        if not job_id:
            logger.warning("Upload progress update missing job_id")
            return

        try:
            # Get job from Redis (fast, no DB connection)
            job = RedisJobStore.get_job(job_id)
            if not job:
                logger.warning(f"Upload progress update for non-existent job: {job_id}")
                return

            # Update progress in Redis only (no DB write)
            RedisJobStore.update_job(job_id, {
                'upload_progress_bytes': bytes_uploaded
            })

            # Broadcast to all subscribers (optional - for multiple clients tracking same job)
            broadcast_job_status(job_id, {
                'status': job.get('status', 'UPLOADING'),
                'upload_progress_bytes': bytes_uploaded,
                'upload_progress_formatted': format_bytes(bytes_uploaded),
                'input_file_size': job.get('file_size', 0),
            })

            logger.debug(f"Upload progress for job {job_id}: {format_bytes(bytes_uploaded)}")

        except Exception as e:
            logger.error(f"Error updating upload progress for job {job_id}: {e}")


def broadcast_job_status(job_id, status_data):
    """
    Broadcast job status update to all subscribed clients.
    Works from both the Flask app and Celery workers via Redis pubsub.
    Also broadcasts full session state to session room for session-based subscriptions.

    Args:
        job_id: The job ID to broadcast to
        status_data: Dict containing status information to broadcast
    """
    import os
    from datetime import datetime

    logger.info(f"[BROADCAST_FUNC] ========== broadcast_job_status CALLED ==========")
    logger.info(f"[BROADCAST_FUNC] Job ID: {job_id}")
    logger.info(f"[BROADCAST_FUNC] Status: {status_data.get('status')}")
    logger.info(f"[BROADCAST_FUNC] SOCKETIO_AVAILABLE: {SOCKETIO_AVAILABLE}")
    logger.info(f"[BROADCAST_FUNC] socketio is None: {socketio is None}")

    # Add job_id to status_data if not present
    if 'job_id' not in status_data:
        status_data['job_id'] = job_id

    room = f"job-{job_id}"

    # Do not gate PROCESSING here; ensure callers calculate ETA before broadcasting

    # If socketio is initialized (we're in the Flask app), use it directly
    if SOCKETIO_AVAILABLE and socketio:
        logger.info(f"[BROADCAST_FUNC] Using Flask app socketio path")
        logger.info(f"[BROADCAST_FUNC] Emitting job_status to room: {room}")
        # Broadcast to job-specific room (legacy per-job subscriptions)
        socketio.emit('job_status', status_data, room=room)
        logger.info(f"[BROADCAST_FUNC] job_status emitted successfully")

        # Log broadcast (but not too verbose)
        subscriber_count = len(active_subscriptions.get(job_id, []))
        logger.info(f"[BROADCAST_FUNC] Subscriber count for job {job_id}: {subscriber_count}")
        if subscriber_count > 0:
            logger.info(f"Broadcast to job {job_id}: status={status_data.get('status')}, subscribers={subscriber_count}")

        # ALSO broadcast to session room (new session-based subscriptions)
        try:
            from utils.redis_job_store import get_session_for_job, get_active_jobs_for_session

            session_key = get_session_for_job(job_id)
            if session_key:
                # Fetch all jobs for this session and broadcast complete state
                jobs = get_active_jobs_for_session(session_key)
                try:
                    jobs = [j for j in jobs if not j.get('dismissed_at')]
                except Exception:
                    pass
                # Force-inject completed_at for COMPLETE jobs if missing
                jobs = _inject_completed_at(jobs)
                session_room = f"session-{session_key}"
                socketio.emit('session_update', {
                    'jobs': jobs,
                    'total': len(jobs),
                    'timestamp': datetime.utcnow().isoformat()
                }, room=session_room)
                logger.debug(f"Broadcast session update to {session_room}: {len(jobs)} jobs")
        except Exception as e:
            logger.warning(f"Failed to broadcast session update for job {job_id}: {e}")

    else:
        # We're in a Celery worker - emit via Redis message queue
        # Flask-SocketIO will pick up these messages and broadcast to connected clients
        logger.info(f"[BROADCAST_FUNC] Using WORKER socketio path (socketio not available in this context)")
        logger.info(f"[BROADCAST_FUNC] SOCKETIO_AVAILABLE={SOCKETIO_AVAILABLE}, socketio={socketio}")
        try:
            logger.info(f"[WORKER BROADCAST] Starting broadcast for job {job_id}, status={status_data.get('status')}")

            # Get or create worker socketio instance
            worker_socketio = _get_worker_socketio()
            if not worker_socketio:
                logger.error(f"[WORKER BROADCAST] Failed to get worker socketio instance")
                return

            # Emit via Redis message queue - Flask app will pick this up
            logger.info(f"[WORKER BROADCAST] Emitting job_status to room {room}")
            worker_socketio.emit('job_status', status_data, room=room, namespace='/')
            logger.info(f"[WORKER BROADCAST] Worker broadcast to job {job_id} via Redis: status={status_data.get('status')}")

            # ALSO broadcast to session room (new session-based subscriptions)
            try:
                logger.info(f"[WORKER BROADCAST] Getting session for job {job_id}")
                from utils.redis_job_store import get_session_for_job, get_active_jobs_for_session

                session_key = get_session_for_job(job_id)
                logger.info(f"[WORKER BROADCAST] Session key for job {job_id}: {session_key}")
                if session_key:
                    # Fetch all jobs for this session and broadcast complete state
                    jobs = get_active_jobs_for_session(session_key)
                    try:
                        jobs = [j for j in jobs if not j.get('dismissed_at')]
                    except Exception:
                        pass
                    # Force-inject completed_at for COMPLETE jobs if missing
                    jobs = _inject_completed_at(jobs)
                    session_room = f"session-{session_key}"
                    logger.info(f"[WORKER BROADCAST] Emitting session_update to room {session_room} with {len(jobs)} jobs")
                    worker_socketio.emit('session_update', {
                        'jobs': jobs,
                        'total': len(jobs),
                        'timestamp': datetime.utcnow().isoformat()
                    }, room=session_room, namespace='/')
                    logger.info(f"[WORKER BROADCAST] Worker broadcast session update to {session_room}: {len(jobs)} jobs")
            except Exception as session_error:
                logger.error(f"[WORKER BROADCAST] Failed to broadcast session update from worker for job {job_id}: {session_error}", exc_info=True)

        except Exception as e:
            logger.error(f"[WORKER BROADCAST] Failed to broadcast from worker for job {job_id}: {e}", exc_info=True)


# Worker-side SocketIO instance (cached)
_worker_socketio_instance = None

def _get_worker_socketio():
    """Get or create a SocketIO instance for worker broadcasts"""
    global _worker_socketio_instance

    if _worker_socketio_instance is not None:
        return _worker_socketio_instance

    try:
        import os
        redis_url = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
        logger.info(f"[WORKER] Initializing worker SocketIO with Redis: {redis_url}")

        # Create SocketIO instance with ONLY message_queue (no Flask app)
        # This is the correct way to emit from external processes
        # Flask-SocketIO will use kombu to publish to Redis
        _worker_socketio_instance = SocketIO(
            message_queue=redis_url,
            logger=True,  # Enable logging to debug
            engineio_logger=True
        )
        logger.info(f"[WORKER] Worker SocketIO instance created successfully")
        return _worker_socketio_instance
    except Exception as e:
        logger.error(f"[WORKER] Failed to create worker SocketIO instance: {e}", exc_info=True)
        return None


def get_active_subscribers(job_id):
    """Get count of active subscribers for a job"""
    return len(active_subscriptions.get(job_id, []))
