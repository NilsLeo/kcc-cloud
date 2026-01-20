# CRITICAL: Apply eventlet monkey patch FIRST, before ANY other imports
# This is required for Flask-SocketIO with eventlet to work properly
# It patches Python's standard library (socket, threading, etc.) to use green threads
import eventlet

eventlet.monkey_patch()

from app import app, socketio

# Routes are already registered in app.py when imported
# No need to call register_routes again here

if __name__ == "__main__":
    socketio.run(app)
