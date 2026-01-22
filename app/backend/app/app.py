"""
"""

import logging
import os
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from utils.routes import register_routes
from utils.socketio_broadcast import broadcast_queue_update as shared_broadcast

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
logger.info("Flask application initialized")

redis_url = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
# Default Socket.IO CORS to '*' unless explicitly set
_socketio_env = os.getenv("SOCKETIO_CORS_ORIGINS", "").strip()
socketio_cors = _socketio_env if _socketio_env else "*"
logger.info(f"Connecting to Redis message queue: {redis_url}")
logger.info(f"SocketIO CORS origins: {socketio_cors}")
socketio = SocketIO(
    app,
    message_queue=redis_url,
    cors_allowed_origins=socketio_cors,
    async_mode="eventlet",
    logger=False,
    engineio_logger=False,
)
logger.info("SocketIO initialized with Redis message queue")

app.config["MAX_CONTENT_LENGTH"] = int(
    os.getenv("MAX_UPLOAD_SIZE", os.getenv("MAX_CONTENT_LENGTH", 1024 * 1024 * 1024))
)  # Default 1GB max upload size
max_size_mb = app.config["MAX_CONTENT_LENGTH"] / (1024 * 1024)
logger.info(f"Max upload size: {max_size_mb:.0f}MB")

# CORS configuration
# Default HTTP CORS to '*' unless explicitly set
_allowed_env = os.getenv("ALLOWED_ORIGINS", "").strip()
if not _allowed_env or _allowed_env == "*":
    allowed_origins = ["*"]
else:
    allowed_origins = [o.strip() for o in _allowed_env.split(",") if o.strip()]
logger.info(f"CORS allowed origins: {allowed_origins}")

CORS(
    app,
    resources={r"/*": {"origins": allowed_origins}},
    methods=["GET", "POST", "OPTIONS", "PATCH", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["Content-Type"],
    max_age=3600,
)

# Ensure data directories exist
storage_path = os.getenv("STORAGE_PATH", "/data")
uploads_path = os.path.join(storage_path, "uploads")
outputs_path = os.path.join(storage_path, "outputs")
os.makedirs(uploads_path, exist_ok=True)
os.makedirs(outputs_path, exist_ok=True)

logger.info(f"Storage configured:")
logger.info(f"  - Base path: {storage_path}")
logger.info(f"  - Uploads: {uploads_path}")
logger.info(f"  - Outputs: {outputs_path}")
logger.info(f"Allowed origins: {allowed_origins}")
logger.info("Testing automated release workflow")

# Register all Flask routes
register_routes(app)


# WebSocket event handlers
@socketio.on("connect")
def handle_connect():
    """Handle client connection."""
    logger.info("Client connected")


@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnection."""
    logger.info("Client disconnected")


@socketio.on("subscribe_queue")
def handle_subscribe_queue():
    """Handle subscription to queue updates - send current queue status."""
    logger.info("Client subscribed to queue updates")
    # Send current queue status immediately
    shared_broadcast()


@socketio.on("request_queue_status")
def handle_request_queue_status():
    """Handle manual queue status request."""
    logger.info("Client requested queue status")
    shared_broadcast()


# Make socketio and broadcast_queue_update available for tasks
app.socketio = socketio
app.broadcast_queue_update = shared_broadcast

if __name__ == "__main__":
    # Development mode
    socketio.run(app, host="0.0.0.0", port=8060, allow_unsafe_werkzeug=True)
