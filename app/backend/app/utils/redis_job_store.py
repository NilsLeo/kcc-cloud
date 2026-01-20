"""
Redis-based job storage for active conversion jobs.

Active jobs are stored in Redis for fast access (<1ms vs 50-100ms DB queries).
Jobs are persisted to PostgreSQL only when they reach terminal states:
- COMPLETE
- DOWNLOADED
- CANCELLED
- ERROR

Benefits:
- Instant job creation (no DB commit latency)
- Fast lookups during upload/processing
- Automatic cleanup via Redis TTL
- Reduced DB load
"""

import json
import os
import redis
from datetime import datetime
from typing import Optional, Dict, Any, List
from utils.enhanced_logger import setup_enhanced_logging, log_with_context

logger = setup_enhanced_logging()

# Initialize Redis client (connects to redis service in docker-compose or Kubernetes)
# Parse Redis hostname from CELERY_BROKER_URL env var for consistency
redis_url = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
redis_host = redis_url.split("://")[1].split(":")[0]  # Extract hostname from URL

try:
    redis_client = redis.Redis(
        host=redis_host,
        port=6379,
        db=0,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
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
        job:{job_id}:ttl -> 24 hours (auto-cleanup via TTL)
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
            session_key = job_data.get("session_key")
            if session_key:
                session_jobs_key = f"session:{session_key}:jobs"
                redis_client.sadd(session_jobs_key, job_id)
                redis_client.expire(session_jobs_key, RedisJobStore.JOB_TTL)

            log_with_context(
                logger,
                "info",
                "[RedisJobStore] Job created in Redis",
                job_id=job_id,
                status=job_data.get("status"),
                ttl_hours=RedisJobStore.JOB_TTL // 3600,
            )

            return True

        except Exception as e:
            log_with_context(
                logger,
                "error",
                f"[RedisJobStore] Failed to create job: {e}",
                job_id=job_id,
                error_type=type(e).__name__,
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
                elif key.endswith("_at") and value:
                    # Parse datetime fields
                    try:
                        result[key] = datetime.fromisoformat(value)
                    except Exception:
                        result[key] = value
                elif key in [
                    "file_size",
                    "upload_progress_bytes",
                    "s3_parts_completed",
                    "s3_parts_total",
                ]:
                    # Parse integer fields
                    try:
                        result[key] = int(value) if value else 0
                    except Exception:
                        result[key] = value
                elif key in [
                    "manga_style",
                    "hq",
                    "two_panel",
                    "webtoon",
                    "no_processing",
                    "upscale",
                    "stretch",
                    "autolevel",
                    "black_borders",
                    "white_borders",
                    "force_color",
                    "force_png",
                    "mozjpeg",
                    "no_kepub",
                    "spread_shift",
                    "no_rotate",
                    "rotate_first",
                ]:
                    # Parse boolean fields
                    result[key] = value.lower() == "true" if value else False
                else:
                    result[key] = value

            return result

        except Exception as e:
            log_with_context(
                logger, "error", f"[RedisJobStore] Failed to get job: {e}", job_id=job_id
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
                logger, "error", f"[RedisJobStore] Failed to update job: {e}", job_id=job_id
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
                logger, "info", "[RedisJobStore] Job deleted from Redis", job_id=job_id
            )

            return True

        except Exception as e:
            log_with_context(
                logger, "error", f"[RedisJobStore] Failed to delete job: {e}", job_id=job_id
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
                logger,
                "error",
                f"[RedisJobStore] Failed to get session jobs: {e}",
                session_key=session_key,
            )
            return []

    @staticmethod
    def get_all_active_jobs() -> List[Dict[str, Any]]:
        """
        Get all active jobs globally from Redis (no DB access).

        Includes jobs in QUEUED, UPLOADING, PROCESSING, and COMPLETE states
        (COMPLETE is included so users can immediately download from the queue view).
        Dismissed jobs and terminal states other than COMPLETE are excluded.

        Returns a list of job dicts shaped like queue_update payload items.
        """
        if not redis_client:
            logger.error("[RedisJobStore] Redis unavailable")
            return []

        try:
            jobs: List[Dict[str, Any]] = []
            # Iterate over job:* keys, but exclude suffix keys like job:*:logs
            for key in redis_client.scan_iter(match="job:*"):
                # Only accept keys with exactly one colon: job:{id}
                if key.count(":") != 1:
                    continue
                _, job_id = key.split(":", 1)

                job_data = RedisJobStore.get_job(job_id)
                if not job_data:
                    continue

                # Skip dismissed
                if job_data.get("dismissed_at"):
                    continue

                raw_status = job_data.get("status", "UNKNOWN")
                # Skip terminal states except COMPLETE
                if raw_status in ["DOWNLOADED", "CANCELLED", "ERRORED"]:
                    continue

                # Normalize created_at to JSON-serializable ISO string if present
                _created = job_data.get("created_at", None)
                if _created is not None and hasattr(_created, "isoformat"):
                    _created = _created.isoformat()

                # Decide emitted status (gated PROCESSING requires ETA + processing_at)
                emit_status = raw_status
                emit_proc_at: Any = None
                emit_eta: Any = None
                if raw_status == "PROCESSING":
                    try:
                        proc_at = job_data.get("processing_at") or job_data.get(
                            "processing_started_at"
                        )
                        eta_at = None
                        projected_eta = None
                        raw_pp = job_data.get("processing_progress")
                        if raw_pp:
                            import json as _json

                            parsed = _json.loads(raw_pp) if isinstance(raw_pp, str) else raw_pp
                            eta_at = parsed.get("eta_at")
                            projected_eta = parsed.get("projected_eta")
                        if eta_at is None and projected_eta is None:
                            projected_eta = job_data.get("estimated_duration_seconds")
                        if proc_at and (eta_at is not None or projected_eta is not None):
                            emit_proc_at = proc_at
                            # Prefer eta_at absolute timestamp; fallback to seconds
                            if eta_at is not None:
                                emit_eta = str(eta_at)
                            else:
                                emit_eta = (
                                    int(projected_eta)
                                    if isinstance(projected_eta, (int, str))
                                    else projected_eta
                                )
                        else:
                            emit_status = "QUEUED"
                    except Exception:
                        emit_status = "QUEUED"

                job_dict: Dict[str, Any] = {
                    "job_id": job_id,
                    "filename": job_data.get("input_filename", ""),
                    "status": emit_status,
                    "device_profile": job_data.get("device_profile", ""),
                    "file_size": int(job_data.get("file_size", 0) or 0),
                    "created_at": _created,
                }

                if emit_status == "PROCESSING" and (
                    emit_proc_at is not None and emit_eta is not None
                ):
                    # Provide only timestamps: processing_at and eta_at (absolute).
                    # FE will do all math.
                    proc_iso = (
                        emit_proc_at.isoformat()
                        if hasattr(emit_proc_at, "isoformat")
                        else str(emit_proc_at)
                    )
                    if proc_iso and (
                        "Z" not in proc_iso
                        and "+" not in proc_iso
                        and "-" not in proc_iso.split("T")[-1]
                    ):
                        proc_iso = proc_iso + "Z"
                    job_dict["processing_at"] = proc_iso

                    # Compute eta_at string if needed
                    if isinstance(emit_eta, str):
                        eta_at_str = emit_eta
                    else:
                        try:
                            from datetime import datetime, timedelta

                            base = proc_iso
                            if base.endswith("Z"):
                                base = base[:-1] + "+00:00"
                            eta_at_str = (
                                datetime.fromisoformat(base) + timedelta(seconds=int(emit_eta))
                            ).isoformat()
                        except Exception:
                            eta_at_str = None
                    if eta_at_str is not None and (
                        "Z" not in eta_at_str
                        and "+" not in eta_at_str
                        and "-" not in eta_at_str.split("T")[-1]
                    ):
                        eta_at_str = eta_at_str + "Z"
                    if eta_at_str is not None:
                        job_dict["eta_at"] = eta_at_str

                if emit_status == "UPLOADING":
                    parts_key = f"multipart_parts:{job_id}"
                    try:
                        parts_count = redis_client.hlen(parts_key)
                    except Exception:
                        parts_count = 0
                    s3_parts_total = int(job_data.get("s3_parts_total", 0) or 0)
                    if parts_count > 0 and s3_parts_total:
                        job_dict["upload_progress"] = {
                            "completed_parts": parts_count,
                            "total_parts": s3_parts_total,
                            "uploaded_bytes": int(job_data.get("upload_progress_bytes", 0) or 0),
                            "total_bytes": int(job_data.get("file_size", 0) or 0),
                            "percentage": round((parts_count / s3_parts_total) * 100, 1),
                        }

                if emit_status == "COMPLETE":
                    job_dict["output_filename"] = job_data.get("output_filename", "")
                    job_dict["output_file_size"] = int(job_data.get("output_file_size", 0) or 0)
                    try:
                        completed_at = job_data.get("completed_at")
                        if completed_at:
                            job_dict["completed_at"] = (
                                completed_at.isoformat()
                                if hasattr(completed_at, "isoformat")
                                else str(completed_at)
                            )
                    except Exception:
                        pass

                jobs.append(job_dict)

            # Sort by created_at if present, else by job_id stable order;
            # newest first not guaranteed via Redis
            try:

                def _key(j):
                    return j.get("created_at") or ""

                jobs.sort(key=_key, reverse=True)
            except Exception:
                pass

            return jobs

        except Exception as e:
            logger.error(f"[RedisJobStore] Failed to list active jobs: {e}")
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
        terminal_states = ["COMPLETE", "DOWNLOADED", "CANCELLED", "ERROR"]
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
                    job_data_copy = {k: v for k, v in job_data.items() if k != "id"}

                    # Map Redis field names to DB model field names
                    if "file_size" in job_data_copy:
                        job_data_copy["input_file_size"] = job_data_copy.pop("file_size")

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
                                item = {"level": "INFO", "message": str(raw), "source": "backend"}

                            entry = LogEntry(
                                level=item.get("level", "INFO"),
                                message=item.get("message", ""),
                                source=item.get("source", "backend"),
                                job_id=job_id,
                                user_id=item.get("user_id"),
                                context=item.get("context") or None,
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
                    logger.warning(
                        f"[RedisJobStore] Failed to persist logs for job "
                        f"{job_id}: {log_persist_error}"
                    )

                log_with_context(
                    logger,
                    "info",
                    "[RedisJobStore] Job persisted to database",
                    job_id=job_id,
                    status=job_data.get("status"),
                )

                # Clean up Redis: remove from session set only for truly terminal
                # states (not COMPLETE). COMPLETE jobs should remain visible so
                # users can download them
                status = job_data.get("status", "")
                if status in ["DOWNLOADED", "CANCELLED", "ERRORED"]:
                    session_key = job_data.get("session_key")
                    if session_key and redis_client:
                        try:
                            session_jobs_key = f"session:{session_key}:jobs"
                            redis_client.srem(session_jobs_key, job_id)
                            log_with_context(
                                logger,
                                "info",
                                "[RedisJobStore] Removed terminal job from session set",
                                job_id=job_id,
                                status=status,
                            )
                        except Exception as cleanup_error:
                            logger.warning(
                                f"Failed to cleanup session set for job {job_id}: {cleanup_error}"
                            )

                return True

            except Exception as e:
                db.rollback()
                log_with_context(
                    logger,
                    "error",
                    f"[RedisJobStore] Failed to persist job to DB: {e}",
                    job_id=job_id,
                    error_type=type(e).__name__,
                )
                return False
            finally:
                db.close()

        except Exception as e:
            log_with_context(
                logger, "error", f"[RedisJobStore] Failed to import DB modules: {e}", job_id=job_id
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
        session_key = redis_client.hget(job_key, "session_key")
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
                logger,
                "info",
                "[RedisJobStore] Cancellation lock acquired",
                session_key=session_key,
                job_id=job_id,
            )
            return True
        else:
            active_job_id = redis_client.get(lock_key)
            log_with_context(
                logger,
                "warning",
                "[RedisJobStore] Cancellation already in progress",
                session_key=session_key,
                requested_job_id=job_id,
                active_job_id=active_job_id,
            )
            return False

    except Exception as e:
        log_with_context(
            logger,
            "error",
            f"[RedisJobStore] Failed to acquire cancellation lock: {e}",
            session_key=session_key,
            job_id=job_id,
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
                logger,
                "info",
                "[RedisJobStore] Cancellation lock released",
                session_key=session_key,
                job_id=job_id,
            )
            return True
        else:
            log_with_context(
                logger,
                "warning",
                "[RedisJobStore] Lock release attempted by non-holder",
                session_key=session_key,
                requested_job_id=job_id,
                current_holder=current_lock_holder,
            )
            return False

    except Exception as e:
        log_with_context(
            logger,
            "error",
            f"[RedisJobStore] Failed to release cancellation lock: {e}",
            session_key=session_key,
            job_id=job_id,
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
            dismissed_at = job_data.get("dismissed_at")
            if dismissed_at:
                logger.debug(f"Skipping dismissed job {job_id} (status {job_data.get('status')})")
                continue

            # Skip jobs in terminal states EXCEPT COMPLETE (users need to see COMPLETE jobs)
            raw_status = job_data.get("status", "UNKNOWN")
            if raw_status in ["DOWNLOADED", "CANCELLED", "ERRORED"]:
                logger.debug(f"Skipping terminal state job {job_id} with status {raw_status}")
                continue

            # Format job for API response (same format as /api/queue/status)
            # Normalize datetime fields to JSON-serializable strings
            _created = job_data.get("created_at")
            if _created is not None and hasattr(_created, "isoformat"):
                _created = _created.isoformat()

            # Compute emitted status with gating for PROCESSING (requires ETA + processing_at)
            emit_status = raw_status
            emit_proc_at: Any = None
            emit_eta: Any = None
            if raw_status == "PROCESSING":
                try:
                    proc_at = job_data.get("processing_at") or job_data.get("processing_started_at")
                    eta_at = None
                    projected_eta = None
                    raw_pp = job_data.get("processing_progress")
                    if raw_pp:
                        import json as _json

                        parsed = _json.loads(raw_pp) if isinstance(raw_pp, str) else raw_pp
                        eta_at = parsed.get("eta_at")
                        projected_eta = parsed.get("projected_eta")
                    if eta_at is None and projected_eta is None:
                        projected_eta = job_data.get("estimated_duration_seconds")
                    if proc_at and (eta_at is not None or projected_eta is not None):
                        emit_proc_at = proc_at
                        if eta_at is not None:
                            emit_eta = str(eta_at)
                        else:
                            emit_eta = (
                                int(projected_eta)
                                if isinstance(projected_eta, (int, str))
                                else projected_eta
                            )
                    else:
                        emit_status = "QUEUED"
                except Exception:
                    emit_status = "QUEUED"

            job_dict = {
                "job_id": job_id,
                "filename": job_data.get("input_filename", ""),
                "status": emit_status,
                "device_profile": job_data.get("device_profile", ""),
                "file_size": int(job_data.get("file_size", 0)),
                "created_at": _created,
            }

            # Mark dismissal flag for COMPLETE jobs
            if emit_status == "COMPLETE":
                job_dict["is_dismissed"] = True if dismissed_at else False

            # Add status-specific fields based on emitted status
            status = emit_status

            if status == "QUEUED":
                # Worker download speed for simulating download progress
                from utils.network_speed import get_download_speed_mbps

                job_dict["worker_download_speed_mbps"] = get_download_speed_mbps()

            if status == "UPLOADING":
                # Upload progress from Redis multipart tracking
                parts_key = f"multipart_parts:{job_id}"
                parts_count = redis_client.hlen(parts_key) if redis_client else 0
                s3_parts_total = int(job_data.get("s3_parts_total", 0))

                if parts_count > 0 and s3_parts_total:
                    job_dict["upload_progress"] = {
                        "completed_parts": parts_count,
                        "total_parts": s3_parts_total,
                        "uploaded_bytes": int(job_data.get("upload_progress_bytes", 0)),
                        "total_bytes": int(job_data.get("file_size", 0)),
                        "percentage": round((parts_count / s3_parts_total) * 100, 1),
                    }

            if emit_status == "PROCESSING" and (emit_proc_at is not None and emit_eta is not None):
                proc_iso = (
                    emit_proc_at.isoformat()
                    if hasattr(emit_proc_at, "isoformat")
                    else str(emit_proc_at)
                )
                if proc_iso and (
                    "Z" not in proc_iso
                    and "+" not in proc_iso
                    and "-" not in proc_iso.split("T")[-1]
                ):
                    proc_iso = proc_iso + "Z"
                job_dict["processing_at"] = proc_iso
                if isinstance(emit_eta, str):
                    eta_at_str = emit_eta
                else:
                    try:
                        from datetime import datetime, timedelta

                        base = proc_iso
                        if base.endswith("Z"):
                            base = base[:-1] + "+00:00"
                        eta_at_str = (
                            datetime.fromisoformat(base) + timedelta(seconds=int(emit_eta))
                        ).isoformat()
                    except Exception:
                        eta_at_str = None
                if eta_at_str is not None and (
                    "Z" not in eta_at_str
                    and "+" not in eta_at_str
                    and "-" not in eta_at_str.split("T")[-1]
                ):
                    eta_at_str = eta_at_str + "Z"
                if eta_at_str is not None:
                    job_dict["eta_at"] = eta_at_str

            if status == "COMPLETE":
                # Output file info
                job_dict["output_filename"] = job_data.get("output_filename", "")
                job_dict["output_file_size"] = int(job_data.get("output_file_size", 0))
                # Include completion timestamp if present, with robust DB fallback
                try:
                    completed_at = job_data.get("completed_at")
                    if completed_at:
                        if hasattr(completed_at, "isoformat"):
                            job_dict["completed_at"] = completed_at.isoformat()
                        else:
                            job_dict["completed_at"] = str(completed_at)
                except Exception:
                    # Ignore and attempt DB fallback below
                    pass
                # Final safeguard: DB fallback if still missing
                if "completed_at" not in job_dict:
                    try:
                        from database import get_db_session, ConversionJob

                        db2 = get_db_session()
                        try:
                            j = db2.query(ConversionJob).get(job_id)
                            if j and j.completed_at:
                                job_dict["completed_at"] = j.completed_at.isoformat()
                        finally:
                            db2.close()
                    except Exception:
                        pass
                # Include dismissed timestamp if present
                try:
                    dismissed_at = job_data.get("dismissed_at")
                    if dismissed_at:
                        # If it's a datetime, convert to ISO
                        if hasattr(dismissed_at, "isoformat"):
                            job_dict["dismissed_at"] = dismissed_at.isoformat()
                        else:
                            job_dict["dismissed_at"] = str(dismissed_at)
                except Exception:
                    pass

                # Generate download URL
                output_filename = job_data.get("output_filename")
                if output_filename:
                    try:
                        from utils.storage.s3_storage import S3Storage

                        storage = S3Storage()
                        # Construct full S3 path: session_key/job_id/output/filename
                        s3_key = f"{session_key}/{job_id}/output/{output_filename}"
                        download_url = storage.presigned_url(s3_key, expires=604800)  # 7 days
                        job_dict["download_url"] = download_url
                    except Exception as e:
                        logger.error(f"Failed to generate download URL for job {job_id}: {e}")

            jobs.append(job_dict)

        return jobs

    except Exception as e:
        logger.error(f"[RedisJobStore] Failed to get active jobs for session: {e}")
        return []


# Module-level helper for broadcaster compatibility
def get_all_active_jobs() -> List[Dict[str, Any]]:
    """Return all active jobs using Redis only (no DB)."""
    return RedisJobStore.get_all_active_jobs()
