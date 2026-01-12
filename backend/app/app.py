import logging
import os
import threading
import time
from datetime import datetime
from flask import Flask
from flask_cors import CORS
from utils.globals import UPLOADS_DIRECTORY
from utils.enhanced_logger import setup_enhanced_logging, log_with_context
from utils.websocket import init_socketio
from utils.routes import register_routes

app = Flask(__name__)
socketio = init_socketio(app)
logger = setup_enhanced_logging()

app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")
app.config["MAX_CONTENT_LENGTH"] = int(
    os.getenv("MAX_CONTENT_LENGTH", 1024 * 1024 * 1024)
)  # Default 1GB

allowed_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",")]

CORS(
    app,
    resources={r"/*": {"origins": allowed_origins}},
    supports_credentials=True,
    methods=["GET", "POST", "OPTIONS", "PATCH", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-Session-Key", "X-Clerk-User-Id"],
    expose_headers=["Content-Type", "X-Session-Key"],
    max_age=3600,
)

os.makedirs(UPLOADS_DIRECTORY, exist_ok=True)

# Initialize S3 storage early to ensure buckets exist
try:
    from utils.storage.s3_storage import S3Storage
    logger.info("[App] Initializing S3 storage and ensuring buckets exist...")
    _ = S3Storage()  # Initialize singleton - this will create buckets if needed
    logger.info("[App] S3 storage initialized successfully")
except Exception as e:
    logger.error(f"[App] Warning: S3 storage initialization failed: {e}")
    # Don't fail app startup if S3 is unavailable

# Daily ML model retraining scheduler (background thread)
def ml_model_retraining_scheduler():
    """
    Background thread that triggers ML model retraining once per day at 3 AM.

    Instead of training directly (which would block the backend), this scheduler
    dispatches a Celery task to the worker queue. The actual training happens
    asynchronously in a Celery worker process.
    """
    log_with_context(logger, 'info', '🔄 ML model retraining scheduler started (daily at 3 AM)')

    while True:
        try:
            now = datetime.now()
            # Check if it's 3 AM (within a 1-hour window to avoid missing it)
            if 3 <= now.hour < 4:
                log_with_context(logger, 'info', '🤖 Triggering daily ML model retraining (Celery task)')

                try:
                    # Import and dispatch the Celery task
                    from tasks import train_ml_model_task

                    # Trigger async task - this returns immediately without blocking
                    result = train_ml_model_task.delay()

                    log_with_context(
                        logger, 'info', '✅ ML model training task dispatched to Celery',
                        task_id=result.id
                    )

                except Exception as e:
                    log_with_context(
                        logger, 'error', f'❌ Failed to dispatch ML training task: {str(e)}',
                        error_type=type(e).__name__
                    )

                # Sleep for 1 hour to avoid triggering multiple times
                time.sleep(3600)

            # Check every 10 minutes
            time.sleep(600)

        except Exception as e:
            log_with_context(
                logger, 'error', f'ML retraining scheduler error: {str(e)}',
                error_type=type(e).__name__
            )
            # Sleep and continue
            time.sleep(600)

# Start ML retraining scheduler in background thread (daemon so it exits with app)
retraining_thread = threading.Thread(target=ml_model_retraining_scheduler, daemon=True)
retraining_thread.start()
log_with_context(logger, 'info', '✅ ML model retraining scheduler thread started')

# Job abandonment is now handled exclusively via WebSocket disconnect events
# See utils/websocket.py:handle_disconnect() for abandonment logic
# Grace period: 1 minute after all clients disconnect
# This polling-based checker has been disabled to simplify architecture
log_with_context(logger, 'info', '✅ Job abandonment handled via WebSocket disconnect events (1-minute grace period)')

# Start Celery event listener to monitor task states and broadcast WebSocket updates
# This replaces the worker-side Redis pub/sub broadcasts with centralized backend monitoring
try:
    from celery_config import celery_app
    from utils.celery_events import start_celery_event_listener
    start_celery_event_listener(celery_app)
except Exception as e:
    log_with_context(logger, 'error', f'Failed to start Celery event listener: {str(e)}',
                     error_type=type(e).__name__)

# Register routes (must be outside __main__ so gunicorn can find them)
register_routes(app)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8060, allow_unsafe_werkzeug=True)
