"""
Celery configuration for MangaConverter task queue.

This module configures Celery to use Redis as the message broker and PostgreSQL
as the result backend for distributed task processing.
"""

import os
from celery import Celery
from kombu import Queue, Exchange

# Redis broker URL from environment
# Default to localhost for development, override in production
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

# PostgreSQL backend for task results
# Uses the same database connection as the main application
DATABASE_URL = os.getenv("DATABASE_PUBLIC_URL")

# Initialize Celery application
celery_app = Celery(
    "mangaconverter",
    broker=CELERY_BROKER_URL,
    backend=f"db+{DATABASE_URL}" if DATABASE_URL else None,
)

# --------------------------
# Explicit queue definitions
# --------------------------
celery_app.conf.task_queues = [
    Queue("conversion", Exchange("conversion", type="direct"), routing_key="conversion"),
    Queue("s3_tasks", Exchange("s3_tasks", type="direct"), routing_key="s3_tasks"),
]
celery_app.conf.task_default_queue = "conversion"
celery_app.conf.task_default_exchange = "conversion"
celery_app.conf.task_default_routing_key = "conversion"

# --------------------------
# Celery configuration
# --------------------------
celery_app.conf.update(
    # Timezone settings
    timezone="UTC",
    enable_utc=True,
    # Serialization settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Task execution settings
    task_track_started=True,  # Track when tasks start, not just when they complete
    task_acks_late=True,  # Acknowledge tasks after completion (more reliable)
    worker_prefetch_multiplier=1,  # Workers fetch one task at a time (prevents hoarding)
    # Workers send task events for monitoring (required for event listener)
    worker_send_task_events=True,
    # Result backend settings
    result_expires=86400,  # Results expire after 24 hours (1 day)
    result_backend_always_retry=True,  # Retry result backend operations on failure
    result_backend_max_retries=10,  # Maximum retries for result backend operations
    # Task time limits (prevent runaway tasks)
    task_time_limit=28800,  # Hard limit: 8 hours (task killed)
    task_soft_time_limit=27000,  # Soft limit: 7.5 hours (exception raised)
    # Worker settings
    worker_disable_rate_limits=True,  # No task-level rate limiting (not used)
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (prevent memory leaks)
    # Task routing and priorities
    task_routes={
        "mangaconverter.convert_file": {"queue": "conversion"},  # Default conversion queue
        "tasks.s3_*": {"queue": "s3_tasks"},
    },
    task_default_priority=5,  # Default priority (0-10, higher = more priority)
    # Periodic tasks (Celery Beat schedule)
    beat_schedule={
        "sync-session-activity-every-5-minutes": {
            "task": "tasks.sync_session_activity",
            "schedule": 300.0,  # Run every 5 minutes (300 seconds)
            "options": {"queue": "conversion"},
        },
    },
    # Logging
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format=(
        "[%(asctime)s: %(levelname)s/%(processName)s]" "[%(task_name)s(%(task_id)s)] %(message)s"
    ),
)


# --------------------------
# Fix for Gunicorn fork issue
# --------------------------
def reset_celery_broker_connection():
    """Close and reset Celery broker connection after Gunicorn fork."""
    try:
        celery_app.connection_or_acquire().release()
    except Exception as e:
        import logging

        logging.warning(f"Failed to reset Celery broker connection after fork: {e}")


try:
    from gunicorn.app.base import BaseApplication  # noqa: F401

    if "gunicorn" in os.environ.get("SERVER_SOFTWARE", ""):
        if hasattr(os, "register_at_fork"):
            os.register_at_fork(after_in_child=reset_celery_broker_connection)
except ImportError:
    pass

# --------------------------
# Import tasks to register them
# --------------------------
try:
    import tasks  # noqa: F401
except ImportError:
    pass
