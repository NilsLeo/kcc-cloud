#!/bin/bash
set -e

# Ensure application data directory exists and is writable by appuser
mkdir -p /data /data/tmp
chown -R appuser:appuser /data || true

# Start supervisord (backend, celery, next, redis)
exec /usr/bin/supervisord -n
