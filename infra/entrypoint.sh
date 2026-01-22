#!/bin/bash
set -e

# Calculate upload size in MB from bytes (default 1GB = 1073741824 bytes)
MAX_UPLOAD_SIZE=${MAX_UPLOAD_SIZE:-1073741824}
export MAX_UPLOAD_SIZE_MB=$((MAX_UPLOAD_SIZE / 1024 / 1024))

echo "Configuring nginx with MAX_UPLOAD_SIZE_MB=${MAX_UPLOAD_SIZE_MB}M"

# Process nginx config template
envsubst '${MAX_UPLOAD_SIZE_MB}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# Test nginx config
nginx -t

# Ensure application data directory exists and is writable by appuser
mkdir -p /data
chown -R appuser:appuser /data || true

# Start supervisord
exec /usr/bin/supervisord -n
