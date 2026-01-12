# Use slim Python base
FROM python:3.11-slim

# Set app root directory
ENV ROOTDIR=/app

# Create non-root user with specific UID/GID
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} appuser 2>/dev/null || groupmod -n appuser $(getent group ${GROUP_ID} | cut -d: -f1) && \
    useradd -u ${USER_ID} -g appuser -s /bin/bash -m appuser || \
    usermod -u ${USER_ID} -g appuser -s /bin/bash -d /home/appuser appuser

# Set working directory
WORKDIR /app

# Install system packages with retry logic
RUN echo "deb http://cdn-fastly.deb.debian.org/debian trixie main contrib non-free" > /etc/apt/sources.list && \
    echo "deb http://security.debian.org/debian-security trixie-security main contrib non-free" >> /etc/apt/sources.list && \
    echo "Acquire::Retries \"3\";" > /etc/apt/apt.conf.d/80-retries && \
    echo "Acquire::http::Timeout \"90\";" >> /etc/apt/apt.conf.d/80-retries && \
    echo "Acquire::ftp::Timeout \"90\";" >> /etc/apt/apt.conf.d/80-retries && \
    apt-get update && apt-get install -y --no-install-recommends \
    p7zip-full \
    unar \
    python3-pil \
    python3-psutil \
    poppler-utils \
    python3-slugify \
    unrar \
    build-essential \
    gcc \
    libffi-dev \
    python3-dev \
    libev-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Remove any stale Python bytecode (prevents issues with old .pyc files)
RUN find /app -depth -name "__pycache__" -exec rm -rf {} + || true

# Copy application code
COPY app /app

# Install Python dependencies
ENV PIP_DEFAULT_TIMEOUT=1000
RUN pip install --retries 5 --no-cache-dir -r /app/requirements.txt
RUN pip install --retries 5 --no-cache-dir -r /app/kcc/requirements.txt

# Note: kindlegen is a proprietary binary and must be volume-mounted at /app/kindlegen/
# It's added to PATH below so it can be found by the application

# Switch to non-root user and add kindlegen directory to PATH
ENV PATH=$PATH:/usr/local/bin:/app/kindlegen
USER appuser

# Launch the app with gunicorn + eventlet worker for WebSocket support
# Using config file with post_fork hook to fix Celery broker connection issue after fork
CMD ["gunicorn", "-c", "gunicorn_config.py", "wsgi:app"]
