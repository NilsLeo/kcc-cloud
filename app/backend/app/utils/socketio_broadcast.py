"""
Shared SocketIO broadcasting utility for both Flask and Celery workers.
"""
import logging
from flask_socketio import SocketIO
from database.models import get_db_session, ConversionJob
from datetime import datetime

logger = logging.getLogger(__name__)

# Create a socketio instance for background tasks
# This connects to the same Redis broker so messages are shared
_socketio_instance = None


def get_socketio_instance():
    """Get or create a SocketIO instance for broadcasting from background tasks."""
    global _socketio_instance

    if _socketio_instance is None:
        import os
        redis_url = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')

        _socketio_instance = SocketIO(
            message_queue=redis_url,
            logger=False,
            engineio_logger=False
        )

    return _socketio_instance


def broadcast_queue_update():
    """
    Broadcast current queue status to all connected clients.
    Can be called from Flask app or Celery workers.
    """
    db = get_db_session()
    try:
        # Get recent jobs (last 100), excluding dismissed ones
        jobs = db.query(ConversionJob).filter(
            ConversionJob.dismissed_at.is_(None)
        ).order_by(ConversionJob.created_at.desc()).limit(100).all()

        jobs_list = []
        for job in jobs:
            job_data = {
                "job_id": job.id,
                "status": job.status.value,
                "filename": job.input_filename,
                "output_filename": job.output_filename,
                "device_profile": job.device_profile,
                "file_size": job.input_file_size,
                "output_file_size": job.output_file_size,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            }

            # Add processing progress for PROCESSING jobs
            if job.status.value == "PROCESSING" and job.processing_started_at and job.estimated_duration_seconds:
                elapsed_seconds = int((datetime.utcnow() - job.processing_started_at).total_seconds())
                estimated_total = job.estimated_duration_seconds
                remaining_seconds = max(0, estimated_total - elapsed_seconds)
                progress_percent = min(100, int((elapsed_seconds / estimated_total) * 100))

                job_data["processing_progress"] = {
                    "elapsed_seconds": elapsed_seconds,
                    "remaining_seconds": remaining_seconds,
                    "projected_eta": remaining_seconds,
                    "progress_percent": progress_percent
                }

            jobs_list.append(job_data)

        queue_status = {
            "jobs": jobs_list,
            "total": len(jobs_list),
            "timestamp": datetime.utcnow().isoformat()
        }

        # Get socketio instance and broadcast
        socketio = get_socketio_instance()
        socketio.emit('queue_update', queue_status)

        logger.info(f"Broadcasted queue update: {len(jobs_list)} jobs")

    except Exception as e:
        logger.error(f"Error broadcasting queue update: {e}")
    finally:
        db.close()
