"""
Celery event listener for monitoring task state changes and broadcasting WebSocket updates.

This module listens to Celery task events (STARTED, SUCCESS, FAILURE, etc.) and:
1. Updates job status in the database
2. Broadcasts status updates to WebSocket clients

This approach is cleaner than having workers broadcast directly:
- Workers focus on processing, backend handles all status updates
- Single source of truth (Celery task states)
- No Redis pub/sub complexity
- Centralized WebSocket broadcast logic
"""

import eventlet
from celery import Celery
from celery.events import EventReceiver
from utils.enhanced_logger import setup_enhanced_logging, log_with_context
from database import create_session_with_retry, ConversionJob
from utils.enums.job_status import JobStatus
from utils.job_status import change_status
import os

logger = setup_enhanced_logging()


class CeleryEventListener:
    """
    Listens for Celery task events and broadcasts WebSocket updates.

    Monitors:
    - task-started: Task picked up by worker → Update to PROCESSING
    - task-succeeded: Task completed successfully → Update to COMPLETE
    - task-failed: Task failed with error → Update to ERRORED
    - task-revoked: Task was cancelled → Update to CANCELLED
    """

    def __init__(self, celery_app):
        """
        Initialize the event listener.

        Args:
            celery_app: Celery application instance
        """
        self.celery_app = celery_app
        self.is_running = False
        self.listener_greenlet = None

    def start(self):
        """Start the event listener in a background greenlet."""
        if self.is_running:
            logger.warning("Celery event listener already running")
            return

        self.is_running = True
        # Use eventlet.spawn() instead of threading.Thread for proper eventlet compatibility
        self.listener_greenlet = eventlet.spawn(self._run_listener)
        logger.info("✅ Celery event listener started")

    def stop(self):
        """Stop the event listener."""
        self.is_running = False
        if self.listener_greenlet:
            self.listener_greenlet.kill()
        logger.info("Celery event listener stopped")

    def _run_listener(self):
        """Main event listener loop (runs in background thread)."""
        try:
            with self.celery_app.connection() as connection:
                receiver = EventReceiver(
                    connection,
                    handlers={
                        'task-received': self._on_task_received,  # Worker pulled task from queue
                        'task-succeeded': self._on_task_succeeded,
                        'task-failed': self._on_task_failed,
                        'task-revoked': self._on_task_revoked,
                    }
                )

                logger.info("🎧 Celery event listener connected and waiting for events...")

                # Capture events and dispatch to handlers
                for _ in receiver.itercapture(limit=None, timeout=None, wakeup=True):
                    if not self.is_running:
                        break

        except Exception as e:
            logger.error(f"Celery event listener error: {e}", exc_info=True)
            self.is_running = False

    def _on_task_received(self, event):
        """
        Handle task-received event: Worker pulled task from queue and is about to execute it.

        Event data:
        - uuid: Task ID
        - name: Task name (e.g., 'mangaconverter.convert_file')
        - args: Task arguments (may be empty in event)
        - kwargs: Keyword arguments (may be empty in event)
        - argsrepr: String representation of args
        - kwargsrepr: String representation of kwargs
        - hostname: Worker hostname
        """
        try:
            task_id = event['uuid']
            task_name = event.get('name', '')

            # Only handle conversion tasks
            if 'convert_file' not in task_name:
                return

            # Extract job_id from kwargs (tasks are invoked with keyword arguments)
            job_id = None

            task_kwargs = event.get('kwargs')
            if task_kwargs:
                try:
                    # kwargs is already a dict in the event data
                    if isinstance(task_kwargs, dict):
                        job_id = task_kwargs.get('job_id')
                        logger.info(f"[CELERY EVENT] Extracted job_id from kwargs dict: {job_id}")
                    # If it's a string representation of a Python dict, use ast.literal_eval
                    elif isinstance(task_kwargs, str):
                        import ast
                        kwargs_dict = ast.literal_eval(task_kwargs)
                        job_id = kwargs_dict.get('job_id')
                        logger.info(f"[CELERY EVENT] Extracted job_id from kwargs string: {job_id}")
                except Exception as e:
                    logger.error(f"[CELERY EVENT] Failed to extract job_id from kwargs: {e}, type={type(task_kwargs)}")

            if not job_id:
                logger.warning(f"[CELERY EVENT] Unable to extract job_id from task-received event for {task_id}")
                return

            logger.info(f"[CELERY EVENT] Task received by worker: {task_id} → job {job_id}")

            # DO NOT update to PROCESSING here - worker will update after calculating ETA
            # This ensures PROCESSING status is never visible without ETA data
            logger.info(f"[CELERY EVENT] Skipping status update - worker will update to PROCESSING with ETA")

        except Exception as e:
            logger.error(f"Error handling task-received event: {e}", exc_info=True)

    def _on_task_succeeded(self, event):
        """
        Handle task-succeeded event: Task completed successfully.

        Event data:
        - uuid: Task ID
        - result: Task return value
        """
        try:
            task_id = event['uuid']
            result = event.get('result', {})

            # Result might be a string or dict, handle both cases
            if isinstance(result, dict):
                job_id = result.get('job_id')
            else:
                # If result is not a dict, try to get it from AsyncResult
                async_result = self.celery_app.AsyncResult(task_id)
                if async_result and hasattr(async_result, 'result') and isinstance(async_result.result, dict):
                    job_id = async_result.result.get('job_id')
                else:
                    logger.warning(f"Cannot extract job_id from task result for {task_id}, result type: {type(result)}")
                    return

            if not job_id:
                logger.warning(f"No job_id in task result for {task_id}")
                return

            logger.info(f"[CELERY EVENT] Task succeeded: {task_id} → job {job_id}")

            # Update job status to COMPLETE
            db = create_session_with_retry()
            try:
                job = db.query(ConversionJob).filter_by(id=job_id).first()
                if job:
                    change_status(job, JobStatus.COMPLETE, db, context={
                        'source': 'celery_event_listener',
                        'task_id': task_id,
                        'event': 'task-succeeded'
                    })
                    logger.info(f"[CELERY EVENT] Updated job {job_id} to COMPLETE")
                else:
                    logger.warning(f"[CELERY EVENT] Job {job_id} not found for task {task_id}")
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error handling task-succeeded event: {e}", exc_info=True)

    def _on_task_failed(self, event):
        """
        Handle task-failed event: Task failed with an error.

        Event data:
        - uuid: Task ID
        - exception: Exception type
        - traceback: Stack trace
        """
        try:
            task_id = event['uuid']
            exception = event.get('exception', 'Unknown error')

            # Get job_id from task arguments or task meta
            result = self.celery_app.AsyncResult(task_id)
            job_id = None

            # First try task args (more reliable)
            if result:
                try:
                    job_id = result.args[0] if result.args and len(result.args) > 0 else None
                except (AttributeError, IndexError):
                    pass

            # Fallback to result.info if available
            if not job_id and result and hasattr(result, 'info') and isinstance(result.info, dict):
                job_id = result.info.get('job_id')

            if not job_id:
                logger.warning(f"[CELERY EVENT] Cannot extract job_id from failed task {task_id}")
                return

            logger.error(f"[CELERY EVENT] Task failed: {task_id} → job {job_id}, error: {exception}")

            # Update job status to ERRORED
            db = create_session_with_retry()
            try:
                job = db.query(ConversionJob).filter_by(id=job_id).first()
                if job:
                    # Don't mark as errored if already successfully completed
                    # This prevents race conditions where task-failed events arrive after job completes
                    if job.status in [JobStatus.COMPLETE, JobStatus.DOWNLOADED]:
                        logger.warning(
                            f"[CELERY EVENT] Ignoring task-failed for job {job_id} - "
                            f"already in terminal success state {job.status.value}"
                        )
                        return

                    job.error_message = str(exception)
                    change_status(job, JobStatus.ERRORED, db, context={
                        'source': 'celery_event_listener',
                        'task_id': task_id,
                        'event': 'task-failed',
                        'error': exception
                    })
                    logger.info(f"[CELERY EVENT] Updated job {job_id} to ERRORED")
                else:
                    logger.warning(f"[CELERY EVENT] Job {job_id} not found for task {task_id}")
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error handling task-failed event: {e}", exc_info=True)

    def _on_task_revoked(self, event):
        """
        Handle task-revoked event: Task was cancelled.

        Event data:
        - uuid: Task ID
        - terminated: Whether task was terminated
        """
        try:
            task_id = event['uuid']

            # Get job_id from task arguments
            result = self.celery_app.AsyncResult(task_id)
            if not result:
                logger.warning(f"[CELERY EVENT] No AsyncResult for revoked task {task_id}")
                return

            # Try to get job_id from task args
            try:
                job_id = result.args[0] if result.args and len(result.args) > 0 else None
            except (AttributeError, IndexError):
                job_id = None

            if not job_id:
                logger.warning(f"[CELERY EVENT] No job_id in task args for revoked task {task_id}")
                return

            logger.info(f"[CELERY EVENT] Task revoked: {task_id} → job {job_id}")

            # Update job status to CANCELLED
            db = create_session_with_retry()
            try:
                job = db.query(ConversionJob).filter_by(id=job_id).first()
                if job:
                    change_status(job, JobStatus.CANCELLED, db, context={
                        'source': 'celery_event_listener',
                        'task_id': task_id,
                        'event': 'task-revoked'
                    })
                    logger.info(f"[CELERY EVENT] Updated job {job_id} to CANCELLED")
                else:
                    logger.warning(f"[CELERY EVENT] Job {job_id} not found for task {task_id}")
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error handling task-revoked event: {e}", exc_info=True)


# Global event listener instance
_event_listener = None


def start_celery_event_listener(celery_app):
    """
    Start the Celery event listener (call this from app.py).

    Args:
        celery_app: Celery application instance
    """
    global _event_listener

    if _event_listener is None:
        _event_listener = CeleryEventListener(celery_app)
        _event_listener.start()
    else:
        logger.warning("Celery event listener already initialized")


def stop_celery_event_listener():
    """Stop the Celery event listener (cleanup on app shutdown)."""
    global _event_listener

    if _event_listener:
        _event_listener.stop()
        _event_listener = None
