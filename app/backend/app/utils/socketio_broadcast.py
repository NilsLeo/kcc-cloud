"""
Shared SocketIO broadcasting utility for both Flask and Celery workers.
"""

import logging
from flask_socketio import SocketIO
from datetime import datetime

try:
    # Prefer Redis-backed queue data
    from utils.redis_job_store import get_all_active_jobs
except Exception:
    get_all_active_jobs = None

logger = logging.getLogger(__name__)

# Create a socketio instance for background tasks
# This connects to the same Redis broker so messages are shared
_socketio_instance = None


def get_socketio_instance():
    """Get or create a SocketIO instance for broadcasting from background tasks."""
    global _socketio_instance

    if _socketio_instance is None:
        import os

        redis_url = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")

        _socketio_instance = SocketIO(message_queue=redis_url, logger=False, engineio_logger=False)

    return _socketio_instance


def broadcast_queue_update():
    """
    Broadcast current queue status to all connected clients.
    Can be called from Flask app or Celery workers.
    """
    try:
        # Prefer Redis-backed active jobs (global)
        if get_all_active_jobs:
            jobs_list = get_all_active_jobs()
        else:
            jobs_list = []

        # Debug summary to verify PROCESSING gating
        try:
            proc_debug = []
            for j in jobs_list:
                if j.get("status") == "PROCESSING":
                    pp = j.get("processing_progress") or {}
                    proc_debug.append(
                        {
                            "job_id": j.get("job_id"),
                            "has_eta": "projected_eta" in pp
                            and pp.get("projected_eta") is not None,
                            "has_processing_at": "processing_at" in j
                            and j.get("processing_at") is not None,
                        }
                    )
            if proc_debug:
                logger.info(f"[Broadcast] PROCESSING jobs debug: {proc_debug}")
        except Exception:
            pass

        queue_status = {
            "jobs": jobs_list,
            "total": len(jobs_list),
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Get socketio instance and broadcast
        socketio = get_socketio_instance()
        socketio.emit("queue_update", queue_status)

        logger.info(f"Broadcasted queue update: {len(jobs_list)} jobs (Redis)")

    except Exception as e:
        logger.error(f"Error broadcasting queue update: {e}")
