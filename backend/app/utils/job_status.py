"""
Centralized job status management utilities.
"""
from datetime import datetime
from utils.enums.job_status import JobStatus
from utils.enhanced_logger import setup_enhanced_logging, log_with_context
from utils.websocket import broadcast_job_status

logger = setup_enhanced_logging()


def change_status(job, new_status, db, user_id=None, context=None, broadcast=True):
    """
    Centralized function to change job status and log the change.

    Args:
        job: ConversionJob instance
        new_status: JobStatus enum value
        db: Database session
        user_id: User ID for logging (optional)
        context: Additional context for logging (optional)
        broadcast: Whether to broadcast via WebSocket (default True, set False for workers)
    """
    logger.info(f"[CHANGE_STATUS] ===== ENTERED change_status() =====")
    logger.info(f"[CHANGE_STATUS] Job ID: {job.id}")
    logger.info(f"[CHANGE_STATUS] Current status: {job.status.value if job.status else None}")
    logger.info(f"[CHANGE_STATUS] New status: {new_status.value}")
    logger.info(f"[CHANGE_STATUS] broadcast parameter: {broadcast}")
    logger.info(f"[CHANGE_STATUS] context: {context}")

    # Check if this is from the Celery event listener
    is_event_listener = context and context.get('source') == 'celery_event_listener'

    if job.status == new_status:
        # Check if we should still broadcast despite status being unchanged
        should_force_broadcast = False
        reason = None

        # Force broadcast if from event listener
        if is_event_listener and broadcast:
            should_force_broadcast = True
            reason = "event listener"
        # Force broadcast if worker is providing important context data (like ETA)
        elif broadcast and context and ('projected_eta' in context or 'estimated_eta_minutes' in context):
            should_force_broadcast = True
            reason = "worker with ETA data"

        if should_force_broadcast:
            logger.info(f"[CHANGE_STATUS] Status already {new_status.value}, but FORCING BROADCAST ({reason})")

            # Update Redis job store even though DB status unchanged
            from utils.redis_job_store import RedisJobStore
            try:
                # Update Redis with any context data (like projected_eta)
                redis_updates = {'status': new_status.value}
                if context:
                    if 'projected_eta' in context:
                        redis_updates['projected_eta'] = context['projected_eta']
                    if 'estimated_eta_minutes' in context:
                        redis_updates['estimated_eta_minutes'] = context['estimated_eta_minutes']

                # Ensure completed_at is present in Redis when broadcasting COMPLETE again
                if new_status == JobStatus.COMPLETE and getattr(job, 'completed_at', None):
                    completed = job.completed_at
                    try:
                        # Will be converted to isoformat by Redis layer, but normalize here
                        redis_updates['completed_at'] = completed
                    except Exception:
                        pass

                RedisJobStore.update_job(job.id, redis_updates)
                logger.info(f"[CHANGE_STATUS] Updated Redis job store for {job.id}: {redis_updates}")

                # Also update DB with projected_eta if provided
                if 'projected_eta' in context:
                    job.projected_eta = context['projected_eta']
                    db.commit()
                    logger.info(f"[CHANGE_STATUS] Updated DB projected_eta for {job.id}: {context['projected_eta']}")

            except Exception as redis_error:
                logger.warning(f"[CHANGE_STATUS] Failed to update Redis/DB for job {job.id}: {redis_error}")

            # Broadcast status update
            _broadcast_status_update(job, new_status)
            logger.info(f"[CHANGE_STATUS] Forced broadcast completed for job {job.id} ({reason})")
            return
        else:
            logger.info(f"[CHANGE_STATUS] Status already {new_status.value}, EARLY RETURN")
            log_with_context(
                logger, 'debug', f'Status already {new_status.value}, no change needed',
                job_id=job.id,
                user_id=user_id or job.session_key,
                current_status=new_status.value
            )
            return  # No change needed
    
    old_status = job.status.value if job.status else None
    
    # Log the status change attempt
    log_with_context(
        logger, 'info', f'=== STATUS CHANGE: {old_status} -> {new_status.value} ===',
        job_id=job.id,
        user_id=user_id or job.session_key,
        transition=f'{old_status}_to_{new_status.value}',
        filename=job.input_filename,
        device_profile=job.device_profile
    )
    
    job.status = new_status

    # Set timestamp for status transition
    timestamp = datetime.utcnow()
    timestamp_field = None

    if new_status == JobStatus.QUEUED:
        job.queued_at = timestamp
        timestamp_field = 'queued_at'
    elif new_status == JobStatus.UPLOADING:
        job.uploading_at = timestamp
        timestamp_field = 'uploading_at'
    elif new_status == JobStatus.PROCESSING:
        job.processing_at = timestamp
        timestamp_field = 'processing_at'
    elif new_status == JobStatus.COMPLETE:
        job.completed_at = timestamp
        timestamp_field = 'completed_at'
    elif new_status == JobStatus.DOWNLOADED:
        job.downloaded_at = timestamp
        timestamp_field = 'downloaded_at'
    elif new_status == JobStatus.ERRORED:
        job.errored_at = timestamp
        timestamp_field = 'errored_at'
    elif new_status == JobStatus.CANCELLED:
        job.cancelled_at = timestamp
        timestamp_field = 'cancelled_at'
    elif new_status == JobStatus.ABANDONED:
        job.abandoned_at = timestamp
        timestamp_field = 'abandoned_at'

    try:
        db.commit()

        # Update Redis job store with new status AND timestamp AND context data (like projected_eta)
        from utils.redis_job_store import RedisJobStore
        try:
            redis_updates = {'status': new_status.value}
            if timestamp_field:
                redis_updates[timestamp_field] = timestamp

            # Add context data (especially projected_eta for PROCESSING status)
            if context:
                if 'projected_eta' in context:
                    redis_updates['projected_eta'] = context['projected_eta']
                if 'estimated_eta_minutes' in context:
                    redis_updates['estimated_eta_minutes'] = context['estimated_eta_minutes']

            RedisJobStore.update_job(job.id, redis_updates)
            logger.info(f"Updated Redis job store for {job.id}: {redis_updates}")
        except Exception as redis_error:
            # Don't fail the entire operation if Redis update fails
            logger.warning(f"Failed to update Redis for job {job.id}: {redis_error}")

        # Log the successful status change with flow context
        log_context = {
            'old_status': old_status,
            'new_status': new_status.value,
            'status_change_successful': True,
            'filename': job.input_filename,
            'device_profile': job.device_profile
        }
        if context:
            log_context.update(context)
            
        # Add specific context based on status
        if new_status == JobStatus.QUEUED:
            log_context['conversion_ready'] = True
            log_context['note'] = 'Job ready for background processing'
        elif new_status == JobStatus.PROCESSING:
            log_context['conversion_started'] = True
            log_context['note'] = 'Background conversion in progress'
        elif new_status == JobStatus.COMPLETE:
            log_context['conversion_completed'] = True
            log_context['note'] = 'File ready for download'
            
        log_with_context(
            logger, 'info', f'Status transition completed: {old_status} -> {new_status.value}',
            job_id=job.id,
            user_id=user_id or job.session_key,
            **log_context
        )

        # Broadcast status update via WebSocket (if enabled)
        if broadcast:
            _broadcast_status_update(job, new_status)
        else:
            logger.debug(f'Skipping broadcast for job {job.id} (broadcast=False, worker mode)')

    except Exception as e:
        db.rollback()
        log_with_context(
            logger, 'error', f'FAILED status change from {old_status} to {new_status.value}: {str(e)}',
            job_id=job.id,
            user_id=user_id or job.session_key,
            error_type=type(e).__name__,
            status_change_failed=True
        )
        raise


def _broadcast_status_update(job, status):
    """Helper function to broadcast job status via WebSocket"""
    try:
        logger.info(f"[BROADCAST] ========== BROADCAST STARTED ==========")
        logger.info(f"[BROADCAST] Job ID: {job.id}")
        logger.info(f"[BROADCAST] Status: {status.value}")
        from database.models import format_bytes

        upload_progress = getattr(job, 'upload_progress_bytes', 0)
        # Build status data
        status_data = {
            'status': status.value,
            'upload_progress_bytes': upload_progress,
            'upload_progress_formatted': format_bytes(upload_progress) if upload_progress else None,
            'projected_eta': job.projected_eta if job.projected_eta else None,
        }

        # Add time-based data if available
        if job.created_at:
            elapsed = (datetime.utcnow() - job.created_at).total_seconds()
            status_data['elapsed_seconds'] = int(elapsed)

            if job.projected_eta and job.projected_eta > 0:
                remaining = max(0, job.projected_eta - elapsed)
                status_data['remaining_seconds'] = int(remaining)
                status_data['progress_percent'] = min(100, int((elapsed / job.projected_eta) * 100))

        # Add completion data
        if status == JobStatus.COMPLETE:
            if job.output_filename:
                status_data['output_filename'] = job.output_filename
            if hasattr(job, 'output_file_size') and job.output_file_size:
                status_data['output_file_size'] = job.output_file_size
                status_data['output_file_size_formatted'] = format_bytes(job.output_file_size)
            if hasattr(job, 'input_filename') and job.input_filename:
                status_data['input_filename'] = job.input_filename
            if hasattr(job, 'input_file_size') and job.input_file_size:
                status_data['input_file_size'] = job.input_file_size
                status_data['input_file_size_formatted'] = format_bytes(job.input_file_size)
            if hasattr(job, 'actual_duration') and job.actual_duration:
                status_data['actual_duration'] = job.actual_duration
            # Include completed_at explicitly in job broadcast payload
            try:
                if getattr(job, 'completed_at', None):
                    status_data['completed_at'] = job.completed_at.isoformat() if hasattr(job.completed_at, 'isoformat') else str(job.completed_at)
            except Exception:
                pass
            # Include dismissal flag on COMPLETE jobs
            try:
                status_data['is_dismissed'] = True if getattr(job, 'dismissed_at', None) else False
                if getattr(job, 'dismissed_at', None):
                    try:
                        status_data['dismissed_at'] = job.dismissed_at.isoformat()
                    except Exception:
                        status_data['dismissed_at'] = str(job.dismissed_at)
            except Exception:
                status_data['is_dismissed'] = False

            # Generate download URL using standardized session_key prefix
            try:
                from utils.storage.s3_storage import S3Storage
                storage = S3Storage()
                s3_key = f"{job.session_key}/{job.id}/output/{job.output_filename}"
                download_url = storage.presigned_url(
                    s3_key,
                    expires=604800  # 7 days
                )
                status_data['download_url'] = download_url
            except Exception as e:
                logger.error(f"Failed to generate download URL in broadcast: {e}")

        # Add error data
        if status == JobStatus.ERRORED and hasattr(job, 'error_message') and job.error_message:
            status_data['error'] = job.error_message

        # Broadcast
        logger.info(f"[BROADCAST] Calling broadcast_job_status for job {job.id}")
        logger.info(f"[BROADCAST] Status data keys: {list(status_data.keys())}")
        logger.info(f"[BROADCAST] Status data: {status_data}")
        broadcast_job_status(job.id, status_data)
        logger.info(f"[BROADCAST] ========== BROADCAST COMPLETED ==========")
        logger.info(f"[BROADCAST] Job {job.id} broadcast finished")

    except Exception as e:
        # Don't fail the status change if broadcast fails
        logger.error(f"[BROADCAST] Failed to broadcast status update for job {job.id}: {e}", exc_info=True)
