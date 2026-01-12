# CRITICAL: Apply eventlet monkey patch FIRST, before ANY other imports
# This is required for Flask-SocketIO with eventlet to work properly
# It patches Python's standard library (socket, threading, etc.) to use green threads
import eventlet
eventlet.monkey_patch()

# Apply psycogreen patch AFTER eventlet monkey patch
# This patches psycopg2 for eventlet greenlet compatibility
try:
    from psycogreen.eventlet import patch_psycopg
    patch_psycopg()
except ImportError:
    import warnings
    warnings.warn("psycogreen not installed - psycopg2 not patched for eventlet")

from app import app, socketio

# Routes are already registered in app.py when imported
# No need to call register_routes again here

if __name__ == '__main__':
    socketio.run(app)
