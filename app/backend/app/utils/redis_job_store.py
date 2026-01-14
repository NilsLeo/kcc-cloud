"""
Redis-based job storage for active conversion jobs.

Active jobs are stored in Redis for fast access (<1ms vs 50-100ms DB queries).
Jobs are persisted to PostgreSQL only when they reach terminal states:
- COMPLETE
- DOWNLOADED
- CANCELLED
- ERROR
- ABANDONED

Benefits:
- Instant job creation (no DB commit latency)
- Fast lookups during upload/processing
- Automatic cleanup via Redis TTL
- Reduced DB load
"""

import json
import os
import redis
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from utils.enhanced_logger import setup_enhanced_logging, log_with_context

logger = setup_enhanced_logging()

# Initialize Redis client (connects to redis service in docker-compose or Kubernetes)
# Parse Redis hostname from CELERY_BROKER_URL env var for consistency
redis_url = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
redis_host = redis_url.split('://')[1].split(':')[0]  # Extract hostname from URL

try:
    redis_client = redis.Redis(
        host=redis_host,
        port=6379,
        db=0,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5
    )
    redis_client.ping()
    logger.info(f"[RedisJobStore] Redis connection established successfully to {redis_host}")
except Exception as e:
    logger.error(f"[RedisJobStore] Failed to connect to Redis at {redis_host}: {e}")
    redis_client = None


class RedisJobStore:
    """
    Redis-based storage for active conversion jobs.

    Schema:
        job:{job_id} -> Hash with all job fields
        job:{job_id}:ttl -> 24 hours (auto-cleanup abandoned jobs)
        session:{session_key}:jobs -> Set of job_ids for user's jobs
    """

    JOB_TTL = 86400  # 24 hours

    @staticmethod
    def create_job(job_id: str, job_data: Dict[str, Any]) -> bool:
        """
        Create a new job in Redis.

        Args:
            job_id: Unique job identifier
            job_data: Job fields (status, filename, session_key, etc.)

        Returns:
            bool: True if successful
        """
        if not redis_client:
            logger.error("[RedisJobStore] Redis unavailable, cannot create job")
            return False

        try:
            # Convert all values to strings for Redis hash
            redis_data = {}
            for key, value in job_data.items():
                if isinstance(value, datetime):
                    redis_data[key] = value.isoformat()
                elif value is None:
                    redis_data[key] = ""
                elif isinstance(value, (dict, list)):
                    redis_data[key] = json.dumps(value)
                else:
                    redis_data[key] = str(value)

            # Store job data as Redis hash
            job_key = f"job:{job_id}"
            redis_client.hset(job_key, mapping=redis_data)

            # Set TTL for auto-cleanup
            redis_client.expire(job_key, RedisJobStore.JOB_TTL)

            # Add to session's job set for listing
            session_key = job_data.get('session_key')
            if session_key:
                session_jobs_key = f"session:{session_key}:jobs"
                redis_client.sadd(session_jobs_key, job_id)
                redis_client.expire(session_jobs_key, RedisJobStore.JOB_TTL)

            log_with_context(
                logger, 'info', '[RedisJobStore] Job created in Redis',
                job_id=job_id,
                status=job_data.get('status'),
                ttl_hours=RedisJobStore.JOB_TTL // 3600
            )

            return True

        except Exception as e:
            log_with_context(
                logger, 'error', f'[RedisJobStore] Failed to create job: {e}',
                job_id=job_id,
                error_type=type(e).__name__
            )
            return False

    @staticmethod
    def get_job(job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job data from Redis.

        Args:
            job_id: Job identifier

        Returns:
            dict: Job data or None if not found
        """
        if not redis_client:
            return None

        try:
            job_key = f"job:{job_id}"
            job_data = redis_client.hgetall(job_key)

            if not job_data:
                return None

            # Convert string values back to proper types
            result = {}
            for key, value in job_data.items():
                if value == "":
                    result[key] = None
                elif key.endswith('_at') and value:
                    # Parse datetime fields
                    try:
                        result[key] = datetime.fromisoformat(value)
                    except:
                        result[key] = value
                elif key in ['file_size', 'upload_progress_bytes', 's3_parts_completed', 's3_parts_total']:
                    # Parse integer fields
                    try:
                        result[key] = int(value) if value else 0
                    except:
                        result[key] = value
                elif key in ['manga_style', 'hq', 'two_panel', 'webtoon', 'no_processing',
                             'upscale', 'stretch', 'autolevel', 'black_borders', 'white_borders',
                             'force_color', 'force_png', 'mozjpeg', 'no_kepub', 'spread_shift',
                             'no_rotate', 'rotate_first']:
                    # Parse boolean fields
                    result[key] = value.lower() == 'true' if value else False
                else:
                    result[key] = value

            return result

        except Exception as e:
            log_with_context(
                logger, 'error', f'[RedisJobStore] Failed to get job: {e}',
                job_id=job_id
            )
            return None

    @staticmethod
    def update_job(job_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update job fields in Redis.

        Args:
            job_id: Job identifier
            updates: Fields to update

        Returns:
            bool: True if successful
        """
        if not redis_client:
            return False

        try:
            # Convert values to strings
            redis_updates = {}
            for key, value in updates.items():
                if isinstance(value, datetime):
                    redis_updates[key] = value.isoformat()
                elif value is None:
                    redis_updates[key] = ""
                elif isinstance(value, (dict, list)):
                    redis_updates[key] = json.dumps(value)
                else:
                    redis_updates[key] = str(value)

            job_key = f"job:{job_id}"
            redis_client.hset(job_key, mapping=redis_updates)

            return True

        except Exception as e:
            log_with_context(
                logger, 'error', f'[RedisJobStore] Failed to update job: {e}',
                job_id=job_id
            )
            return False

    @staticmethod
    def delete_job(job_id: str, session_key: str = None) -> bool:
        """
        Delete job from Redis.

        Args:
            job_id: Job identifier
            session_key: Optional session key to remove from session set

        Returns:
            bool: True if successful
        """
        if not redis_client:
            return False

        try:
            job_key = f"job:{job_id}"
            redis_client.delete(job_key)

            if session_key:
                session_jobs_key = f"session:{session_key}:jobs"
                redis_client.srem(session_jobs_key, job_id)

            log_with_context(
                logger, 'info', '[RedisJobStore] Job deleted from Redis',
                job_id=job_id
            )

            return True

        except Exception as e:
            log_with_context(
                logger, 'error', f'[RedisJobStore] Failed to delete job: {e}',
                job_id=job_id
            )
            return False

    @staticmethod
    def get_session_jobs(session_key: str) -> List[str]:
        """
        Get all job IDs for a session.

        Args:
            session_key: Session identifier

        Returns:
            list: Job IDs
        """
        if not redis_client:
            return []

        try:
            session_jobs_key = f"session:{session_key}:jobs"
            job_ids = redis_client.smembers(session_jobs_key)
            return list(job_ids)

        except Exception as e:
            log_with_context(
                logger, 'error', f'[RedisJobStore] Failed to get session jobs: {e}',
                session_key=session_key
            )
            return []

    @staticmethod
    def is_terminal_state(status: str) -> bool:
        """
        Check if a job status is terminal (ready for DB persistence).

        Args:
            status: Job status

        Returns:
            bool: True if terminal state
        """
        terminal_states = ['COMPLETE', 'DOWNLOADED', 'CANCELLED', 'ERROR', 'ABANDONED']
        return status in terminal_states

    @staticmethod
    def persist_to_db(job_id: str, job_data: Dict[str, Any]) -> bool:
        """
        Persist job to PostgreSQL database.
        Called when job reaches terminal state.

        Args:
            job_id: Job identifier
            job_data: Job data from Redis

        Returns:
            bool: True if successful
        """
        try:
            # Import via package root for consistency
            from database import ConversionJob, LogEntry, get_db_session

            db = get_db_session()
            try:
                # Check if already exists
                existing_job = db.query(ConversionJob).get(job_id)
                if existing_job:
                    # Update existing record
                    for key, value in job_data.items():
                        if hasattr(existing_job, key):
                            setattr(existing_job, key, value)
                else:
                    # Create new record - remove 'id' and map field names
                    job_data_copy = {k: v for k, v in job_data.items() if k != 'id'}

                    # Map Redis field names to DB model field names
                    if 'file_size' in job_data_copy:
                        job_data_copy['input_file_size'] = job_data_copy.pop('file_size')

                    new_job = ConversionJob(id=job_id, **job_data_copy)
                    db.add(new_job)

                # Flush job changes before inserting logs so FK-less references are consistent
                db.commit()

                # Fetch buffered logs from Redis and persist with the job
                try:
                    import json as _json
                    if redis_client:
                        logs_key = f"job:{job_id}:logs"
                        raw_logs = redis_client.lrange(logs_key, 0, -1)
                    else:
                        raw_logs = []

                    if raw_logs:
                        entries = []
                        for raw in raw_logs:
                            try:
                                item = _json.loads(raw)
                            except Exception:
                                # Best-effort parse; fallback to message-only
                                item = {'level': 'INFO', 'message': str(raw), 'source': 'backend'}

                            entry = LogEntry(
                                level=item.get('level', 'INFO'),
                                message=item.get('message', ''),
                                source=item.get('source', 'backend'),
                                job_id=job_id,
                                user_id=item.get('user_id'),
                                context=item.get('context') or None,
                            )
                            entries.append(entry)

                        if entries:
                            db.add_all(entries)
                            db.commit()

                        # Clear Redis logs after successful persistence
                        try:
                            if redis_client:
                                redis_client.delete(logs_key)
                        except Exception:
                            pass
                except Exception as log_persist_error:
                    # Do not fail the whole operation if logs fail; record warning
                    logger.warning(f"[RedisJobStore] Failed to persist logs for job {job_id}: {log_persist_error}")

                log_with_context(
                    logger, 'info', '[RedisJobStore] Job persisted to database',
                    job_id=job_id,
                    status=job_data.get('status')
                )

                # Clean up Redis: remove from session set only for truly terminal states (not COMPLETE)
                # COMPLETE jobs should remain visible so users can download them
                status = job_data.get('status', '')
                if status in ['DOWNLOADED', 'CANCELLED', 'ERRORED', 'ABANDONED']:
                    session_key = job_data.get('session_key')
                    if session_key and redis_client:
                        try:
                            session_jobs_key = f"session:{session_key}:jobs"
                            redis_client.srem(session_jobs_key, job_id)
                            log_with_context(
                                logger, 'info', '[RedisJobStore] Removed terminal job from session set',
                                job_id=job_id,
                                status=status
                            )
                        except Exception as cleanup_error:
                            logger.warning(f"Failed to cleanup session set for job {job_id}: {cleanup_error}")

                return True

            except Exception as e:
                db.rollback()
                log_with_context(
                    logger, 'error', f'[RedisJobStore] Failed to persist job to DB: {e}',
                    job_id=job_id,
                    error_type=type(e).__name__
                )
                return False
            finally:
                db.close()

        except Exception as e:
            log_with_context(
                logger, 'error', f'[RedisJobStore] Failed to import DB modules: {e}',
                job_id=job_id
            )
            return False


def get_session_for_job(job_id: str) -> Optional[str]:
    """
    Get the session key for a given job ID.

    Args:
        job_id: Job identifier

    Returns:
        Session key or None if not found
    """
    if not redis_client:
        return None

    try:
        job_key = f"job:{job_id}"
        session_key = redis_client.hget(job_key, 'session_key')
        return session_key if session_key else None
    except Exception as e:
        logger.error(f"[RedisJobStore] Failed to get session for job {job_id}: {e}")
        return None


def acquire_cancellation_lock(session_key: str, job_id: str) -> bool:
    """
    Acquire a cancellation lock for a session to prevent concurrent cancellations.

    Args:
        session_key: User's session key
        job_id: Job ID being cancelled

    Returns:
        bool: True if lock acquired, False if another cancellation is in progress
    """
    if not redis_client:
        logger.error("[RedisJobStore] Redis unavailable, cannot acquire cancellation lock")
        return True  # Allow operation if Redis is down

    try:
        lock_key = f"cancellation_lock:{session_key}"
        # Try to set lock with NX (only if not exists) and 30 second TTL
        lock_acquired = redis_client.set(lock_key, job_id, nx=True, ex=30)

        if lock_acquired:
            log_with_context(
                logger, 'info', '[RedisJobStore] Cancellation lock acquired',
                session_key=session_key,
                job_id=job_id
            )
            return True
        else:
            active_job_id = redis_client.get(lock_key)
            log_with_context(
                logger, 'warning', '[RedisJobStore] Cancellation already in progress',
                session_key=session_key,
                requested_job_id=job_id,
                active_job_id=active_job_id
            )
            return False

    except Exception as e:
        log_with_context(
            logger, 'error', f'[RedisJobStore] Failed to acquire cancellation lock: {e}',
            session_key=session_key,
            job_id=job_id
        )
        return True  # Allow operation on error


def release_cancellation_lock(session_key: str, job_id: str) -> bool:
    """
    Release a cancellation lock for a session.

    Args:
        session_key: User's session key
        job_id: Job ID that was being cancelled

    Returns:
        bool: True if lock released successfully
    """
    if not redis_client:
        return True

    try:
        lock_key = f"cancellation_lock:{session_key}"
        # Only delete if the lock is held by this job (prevent race conditions)
        current_lock_holder = redis_client.get(lock_key)

        if current_lock_holder == job_id:
            redis_client.delete(lock_key)
            log_with_context(
                logger, 'info', '[RedisJobStore] Cancellation lock released',
                session_key=session_key,
                job_id=job_id
            )
            return True
        else:
            log_with_context(
                logger, 'warning', '[RedisJobStore] Lock release attempted by non-holder',
                session_key=session_key,
                requested_job_id=job_id,
                current_holder=current_lock_holder
            )
            return False

    except Exception as e:
        log_with_context(
            logger, 'error', f'[RedisJobStore] Failed to release cancellation lock: {e}',
            session_key=session_key,
            job_id=job_id
        )
        return False


def has_active_cancellation(session_key: str) -> Optional[str]:
    """
    Check if there's an active cancellation in progress for this session.

    Args:
        session_key: User's session key

    Returns:
        str: Job ID of active cancellation, or None if no cancellation in progress
    """
    if not redis_client:
        return None

    try:
        lock_key = f"cancellation_lock:{session_key}"
        active_job_id = redis_client.get(lock_key)
        return active_job_id

    except Exception as e:
        logger.error(f"[RedisJobStore] Failed to check cancellation lock: {e}")
        return None


def get_active_jobs_for_session(session_key: str) -> List[Dict[str, Any]]:
    """
    Get all active jobs for a session (formatted for API response).

    Args:
        session_key: User's session key

    Returns:
        List of job dicts with all relevant fields
    """
    if not redis_client:
        logger.error("[RedisJobStore] Redis unavailable")
        return []

    try:
        # Get all job IDs for this session
        session_jobs_key = f"session:{session_key}:jobs"
        job_ids = redis_client.smembers(session_jobs_key)

        if not job_ids:
            return []

        jobs = []
        for job_id in job_ids:
            job_data = RedisJobStore.get_job(job_id)
            if not job_data:
                continue

            # Skip any dismissed jobs (user explicitly dismissed them from UI)
            dismissed_at = job_data.get('dismissed_at')
            if dismissed_at:
                logger.debug(f"Skipping dismissed job {job_id} (status {job_data.get('status')})")
                continue

            # Skip jobs in terminal states EXCEPT COMPLETE (users need to see COMPLETE jobs)
            status = job_data.get('status', 'UNKNOWN')
            if status in ['DOWNLOADED', 'CANCELLED', 'ERRORED', 'ABANDONED']:
                logger.debug(f"Skipping terminal state job {job_id} with status {status}")
                continue

            # Format job for API response (same format as /api/queue/status)
            job_dict = {
                'job_id': job_id,
                'filename': job_data.get('input_filename', ''),
                'status': status,
                'device_profile': job_data.get('device_profile', ''),
                'file_size': int(job_data.get('file_size', 0)),
            }

            # Mark dismissal flag for COMPLETE jobs
            if status == 'COMPLETE':
                job_dict['is_dismissed'] = True if dismissed_at else False

            # Add status-specific fields
            status = job_data.get('status')

            if status == 'QUEUED':
                # Worker download speed for simulating download progress
                from utils.network_speed import get_download_speed_mbps
                job_dict['worker_download_speed_mbps'] = get_download_speed_mbps()

            if status == 'UPLOADING':
                # Upload progress from Redis multipart tracking
                parts_key = f"multipart_parts:{job_id}"
                parts_count = redis_client.hlen(parts_key) if redis_client else 0
                s3_parts_total = int(job_data.get('s3_parts_total', 0))

                if parts_count > 0 and s3_parts_total:
                    job_dict['upload_progress'] = {
                        'completed_parts': parts_count,
                        'total_parts': s3_parts_total,
                        'uploaded_bytes': int(job_data.get('upload_progress_bytes', 0)),
                        'total_bytes': int(job_data.get('file_size', 0)),
                        'percentage': round((parts_count / s3_parts_total) * 100, 1)
                    }

            if status == 'PROCESSING':
                # Processing progress with ETA
                processing_at = job_data.get('processing_at')
                projected_eta = job_data.get('projected_eta')
                if processing_at and projected_eta:
                    try:
                        # processing_at is already a datetime object (parsed by get_job())
                        # Only parse if it's still a string
                        if isinstance(processing_at, str):
                            processing_at = datetime.fromisoformat(processing_at)

                        elapsed_seconds = (datetime.utcnow() - processing_at).total_seconds()
                        projected_eta_seconds = int(float(projected_eta))
                        remaining_seconds = max(0, projected_eta_seconds - elapsed_seconds)

                        job_dict['processing_progress'] = {
                            'elapsed_seconds': int(elapsed_seconds),
                            'remaining_seconds': int(remaining_seconds),
                            'projected_eta': projected_eta_seconds,
                            'progress_percent': min(100, int((elapsed_seconds / projected_eta_seconds) * 100))
                        }
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Failed to parse processing progress for job {job_id}: {e}")

            if status == 'COMPLETE':
                # Output file info
                job_dict['output_filename'] = job_data.get('output_filename', '')
                job_dict['output_file_size'] = int(job_data.get('output_file_size', 0))
                # Include completion timestamp if present, with robust DB fallback
                try:
                    completed_at = job_data.get('completed_at')
                    if completed_at:
                        if hasattr(completed_at, 'isoformat'):
                            job_dict['completed_at'] = completed_at.isoformat()
                        else:
                            job_dict['completed_at'] = str(completed_at)
                except Exception:
                    # Ignore and attempt DB fallback below
                    pass
                # Final safeguard: DB fallback if still missing
                if 'completed_at' not in job_dict:
                    try:
                        from database import get_db_session, ConversionJob
                        db2 = get_db_session()
                        try:
                            j = db2.query(ConversionJob).get(job_id)
                            if j and j.completed_at:
                                job_dict['completed_at'] = j.completed_at.isoformat()
                        finally:
                            db2.close()
                    except Exception:
                        pass
                # Include dismissed timestamp if present
                try:
                    dismissed_at = job_data.get('dismissed_at')
                    if dismissed_at:
                        # If it's a datetime, convert to ISO
                        if hasattr(dismissed_at, 'isoformat'):
                            job_dict['dismissed_at'] = dismissed_at.isoformat()
                        else:
                            job_dict['dismissed_at'] = str(dismissed_at)
                except Exception:
                    pass

                # Generate download URL
                output_filename = job_data.get('output_filename')
                if output_filename:
                    try:
                        from utils.storage.s3_storage import S3Storage
                        storage = S3Storage()
                        # Construct full S3 path: session_key/job_id/output/filename
                        s3_key = f"{session_key}/{job_id}/output/{output_filename}"
                        download_url = storage.presigned_url(
                            s3_key,
                            expires=604800  # 7 days
                        )
                        job_dict['download_url'] = download_url
                    except Exception as e:
                        logger.error(f"Failed to generate download URL for job {job_id}: {e}")

            jobs.append(job_dict)

        return jobs

    except Exception as e:
        logger.error(f"[RedisJobStore] Failed to get active jobs for session: {e}")
        return []
