"""
Celery tasks for MangaConverter background processing.

This module defines Celery tasks that can be executed asynchronously by worker processes.
Tasks are queued via Redis and processed independently from the main Flask application.
"""

from celery_config import celery_app
from utils.utils import process_conversion
from utils.enhanced_logger import setup_enhanced_logging, log_with_context, reinitialize_db_handler
from celery.signals import worker_process_init
import os

# Initialize logging
logger = setup_enhanced_logging()


@worker_process_init.connect
def init_worker_process(**kwargs):
    """
    Reinitialize database handler after Celery forks worker process.

    When Celery uses prefork pool, threads don't survive the fork.
    This signal fires after each worker process is forked, allowing us
    to recreate the DatabaseHandler's background thread.
    """
    print("[tasks] Worker process initialized, reinitializing database logger...")
    reinitialize_db_handler()


@celery_app.task(
    bind=True,
    name='mangaconverter.convert_file',
    max_retries=3,  # Retry up to 3 times on failure
    default_retry_delay=60,  # Wait 60 seconds between retries
    autoretry_for=(Exception,),  # Auto-retry for any exception
    retry_backoff=True,  # Exponential backoff (60s, 120s, 240s)
    retry_backoff_max=600,  # Maximum 10 minutes between retries
    retry_jitter=True  # Add randomness to avoid thundering herd
)
def convert_file_task(self, job_id, upload_name, session_key, options, device_profile, alias):
    """
    Celery task for converting manga/comic files to e-reader formats.

    This task wraps the existing process_conversion function and executes it
    asynchronously in a Celery worker process. The task includes automatic retry
    logic with exponential backoff and provides progress tracking via Celery's task state system.

    Args:
        self: Celery task instance (bound via bind=True)
        job_id (str): Unique job identifier (UUID)
        upload_name (str): Original filename of the uploaded file
        session_key (str): User session identifier for tracking
        options (dict): Conversion options including advanced settings
        device_profile (str): Target device profile (e.g., 'KV', 'KPW5')
        alias (str): Storage identifier (session alias or user ID)

    Returns:
        dict: Task result with status and job_id

    Raises:
        Exception: Any exception from the conversion process (will trigger retry if configured)

    Example:
        >>> from tasks import convert_file_task
        >>> result = convert_file_task.delay(
        ...     job_id='123e4567-e89b-12d3-a456-426614174000',
        ...     upload_name='manga.cbz',
        ...     session_key='session-key-123',
        ...     options={'advanced_options': {}},
        ...     device_profile='KV',
        ...     alias='user-alias'
        ... )
        >>> result.state  # 'PENDING', 'STARTED', 'SUCCESS', or 'FAILURE'
        'PENDING'
        >>> result.ready()  # Check if task completed
        False
    """
    try:
        # Log task start
        log_with_context(
            logger, 'info', 'Celery task started',
            job_id=job_id,
            user_id=session_key,
            task_id=self.request.id,
            task_name=self.name,
            device_profile=device_profile,
            source='worker'
        )

        # Delegate to existing processing logic
        # This function handles all conversion steps:
        # 1. Download input file from S3
        # 2. Extract archives if needed
        # 3. Run KCC conversion
        # 4. Upload output file to S3
        # 5. Update database with results
        process_conversion(
            job_id=job_id,
            upload_name=upload_name,
            session_key=session_key,
            options=options,
            device_profile=device_profile,
            alias=alias
        )

        # Log task completion
        log_with_context(
            logger, 'info', 'Celery task completed successfully',
            job_id=job_id,
            user_id=session_key,
            task_id=self.request.id,
            source='worker'
        )

        return {
            'status': 'success',
            'job_id': job_id,
            'task_id': self.request.id
        }

    except Exception as e:
        # Log task failure
        log_with_context(
            logger, 'error', f'Celery task failed: {str(e)}',
            job_id=job_id,
            user_id=session_key,
            task_id=self.request.id,
            error_type=type(e).__name__,
            error_message=str(e),
            source='worker'
        )

        # Re-raise exception to mark task as failed
        # Celery will handle retries if configured via max_retries
        raise


@celery_app.task(
    bind=True,
    name='tasks.s3_upload_task',
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True
)
def s3_upload_task(self, local_path, s3_key):
    """
    Celery task to upload a file to S3.
    This task is intended to be run on a worker that does not use eventlet,
    to avoid conflicts with boto3.
    """
    from utils.storage.s3_storage import S3Storage
    
    log_with_context(
        logger, 'info', 'S3 upload task started',
        task_id=self.request.id,
        s3_key=s3_key,
        local_path=local_path,
        source='worker'
    )
    
    try:
        storage = S3Storage()
        storage.upload(local_path, s3_key)
        
        log_with_context(
            logger, 'info', 'S3 upload task completed successfully',
            task_id=self.request.id,
            s3_key=s3_key,
            source='worker'
        )

        return {'status': 'success', 's3_key': s3_key}
    except Exception as e:
        log_with_context(
            logger, 'error', f'S3 upload task failed: {str(e)}',
            task_id=self.request.id,
            s3_key=s3_key,
            error_type=type(e).__name__,
            source='worker'
        )
        raise


@celery_app.task(name='tasks.s3_initiate_multipart_upload')
def s3_initiate_multipart_upload_task(key):
    from utils.storage.s3_storage import S3Storage
    storage = S3Storage()
    return storage.initiate_multipart_upload(key)

@celery_app.task(name='tasks.s3_generate_multipart_part_url')
def s3_generate_multipart_part_url_task(key, upload_id, part_number):
    from utils.storage.s3_storage import S3Storage
    storage = S3Storage()
    return storage.generate_multipart_part_url(key, upload_id, part_number)

@celery_app.task(name='tasks.s3_complete_multipart_upload')
def s3_complete_multipart_upload_task(key, upload_id, parts):
    from utils.storage.s3_storage import S3Storage
    storage = S3Storage()
    return storage.complete_multipart_upload(key, upload_id, parts)

@celery_app.task(name='tasks.s3_abort_multipart_upload')
def s3_abort_multipart_upload_task(key, upload_id):
    from utils.storage.s3_storage import S3Storage
    storage = S3Storage()
    storage.abort_multipart_upload(key, upload_id)

@celery_app.task(name='tasks.s3_presigned_url')
def s3_presigned_url_task(key):
    from utils.storage.s3_storage import S3Storage
    storage = S3Storage()
    return storage.presigned_url(key)

@celery_app.task(name='tasks.s3_object_exists')
def s3_object_exists_task(key):
    from utils.storage.s3_storage import S3Storage
    storage = S3Storage()
    return storage.exists(key)

@celery_app.task(name='tasks.s3_get_object_size')
def s3_get_object_size_task(key):
    from utils.storage.s3_storage import S3Storage
    storage = S3Storage()
    return storage.get_object_size(key)

@celery_app.task(name='tasks.s3_copy_to_error_bucket')
def s3_copy_to_error_bucket_task(source_key, error_key=None):
    from utils.storage.s3_storage import S3Storage
    storage = S3Storage()
    return storage.copy_to_error_bucket(source_key, error_key)

@celery_app.task(name='tasks.s3_download_file')
def s3_download_file_task(bucket, key, local_path):
    from utils.storage.s3_storage import S3Storage
    storage = S3Storage()
    storage.client.download_file(bucket, key, local_path)


@celery_app.task(
    bind=True,
    name='tasks.train_ml_model',
    max_retries=0,  # Don't retry training failures
    time_limit=600,  # 10 minute timeout
    soft_time_limit=540  # 9 minute soft limit
)
def train_ml_model_task(self):
    """
    Celery task to train the ML ETA prediction model.

    This runs asynchronously in a Celery worker, preventing it from blocking
    the main backend API. Training typically takes 2-5 minutes depending on
    the dataset size and hyperparameter tuning complexity.

    Returns:
        dict: Training result with status and metrics
    """
    from utils.eta_estimator import train_model

    log_with_context(
        logger, 'info', '🤖 Starting ML model training (Celery task)',
        task_id=self.request.id,
        source='worker'
    )

    try:
        success = train_model()

        if success:
            log_with_context(
                logger, 'info', '✅ ML model training completed successfully',
                task_id=self.request.id,
                source='worker'
            )
            return {'status': 'success', 'message': 'Model trained successfully'}
        else:
            log_with_context(
                logger, 'warning', '⚠️ ML model training skipped (insufficient data)',
                task_id=self.request.id,
                source='worker'
            )
            return {'status': 'skipped', 'message': 'Insufficient training data'}

    except Exception as e:
        log_with_context(
            logger, 'error', f'❌ ML model training failed: {str(e)}',
            task_id=self.request.id,
            error_type=type(e).__name__,
            source='worker'
        )
        return {'status': 'error', 'message': str(e)}


@celery_app.task(
    bind=True,
    name='tasks.sync_session_activity',
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True
)
def sync_session_activity_task(self):
    """
    Periodic Celery task to sync Redis session activity timestamps to PostgreSQL.

    OPTIMIZATION: Reduces DB writes by batching session activity updates
    - WebSocket handlers track activity in Redis (instant, no DB connection)
    - This task syncs Redis → DB every 5 minutes
    - Reduces DB writes from ~100/minute to ~1/5 minutes (99% reduction)

    This task should be configured in Celery Beat schedule to run every 5 minutes.
    """
    import redis
    from datetime import datetime
    from database import create_session_with_retry
    from database.models import Session

    log_with_context(
        logger, 'info', '🔄 Starting session activity sync (Redis → DB)',
        task_id=self.request.id,
        source='worker'
    )

    try:
        redis_client = redis.from_url('redis://redis:6379/0')

        # Scan for all session activity keys
        session_activity_keys = []
        for key in redis_client.scan_iter(match="session:activity:*", count=100):
            session_activity_keys.append(key.decode('utf-8') if isinstance(key, bytes) else key)

        if not session_activity_keys:
            log_with_context(
                logger, 'info', 'No session activity to sync',
                task_id=self.request.id,
                source='worker'
            )
            return {'status': 'success', 'synced_count': 0}

        # Batch update sessions in DB
        db = create_session_with_retry()
        synced_count = 0
        failed_count = 0

        try:
            for redis_key in session_activity_keys:
                # Extract session_key from "session:activity:{session_key}"
                session_key = redis_key.split(':', 2)[2]

                # Get timestamp from Redis
                last_active_iso = redis_client.get(redis_key)
                if not last_active_iso:
                    continue

                if isinstance(last_active_iso, bytes):
                    last_active_iso = last_active_iso.decode('utf-8')

                last_active_dt = datetime.fromisoformat(last_active_iso)

                # Update session in DB
                try:
                    session = db.query(Session).filter(Session.session_key == session_key).first()
                    if session:
                        session.last_used_at = last_active_dt
                        synced_count += 1
                except Exception as update_error:
                    log_with_context(
                        logger, 'warning', f'Failed to update session {session_key[:8]}: {update_error}',
                        task_id=self.request.id,
                        session_key_prefix=session_key[:8],
                        source='worker'
                    )
                    failed_count += 1

            # Commit all updates in one transaction
            db.commit()

            log_with_context(
                logger, 'info', f'✅ Session activity sync completed',
                task_id=self.request.id,
                synced_count=synced_count,
                failed_count=failed_count,
                total_keys=len(session_activity_keys),
                source='worker'
            )

            return {
                'status': 'success',
                'synced_count': synced_count,
                'failed_count': failed_count,
                'total_keys': len(session_activity_keys)
            }

        finally:
            db.close()

    except Exception as e:
        log_with_context(
            logger, 'error', f'❌ Session activity sync failed: {str(e)}',
            task_id=self.request.id,
            error_type=type(e).__name__,
            source='worker'
        )
        raise

