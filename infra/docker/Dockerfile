# ─────────────────────────────────────────────────────────────
# Stage 1: Build NestJS API + Worker (combined — shares node_modules)
# ─────────────────────────────────────────────────────────────
FROM node:20-bullseye-slim AS node-builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends openssl && rm -rf /var/lib/apt/lists/* && npm i -g pnpm
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml tsconfig.json .npmrc ./
COPY packages/ packages/
COPY apps/api/ apps/api/
COPY apps/worker/ apps/worker/
COPY worker-kcc/proto/ worker-kcc/proto/
RUN pnpm install --frozen-lockfile
RUN pnpm --filter @mgc/core build
RUN pnpm --filter @mgc/conversion-sdk build
RUN pnpm --filter @mgc/queue build
RUN pnpm --filter @mgc/events build
RUN pnpm --filter @mgc/db build
RUN pnpm --filter @mgc/db run db:generate
RUN pnpm --filter @mgc/api build
RUN pnpm --filter @mgc/worker build

# ─────────────────────────────────────────────────────────────
# Stage 2: Build Vue frontend
# ─────────────────────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /build
COPY apps/frontend/package.json ./
RUN npm install
COPY apps/frontend/ ./
RUN npm run build

# ─────────────────────────────────────────────────────────────
# Stage 3: Python / KCC setup
# ─────────────────────────────────────────────────────────────
FROM python:3.11-slim-bullseye AS python-builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    git libgl1 libfreetype6 libfontconfig1 p7zip-full \
    && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir "grpcio>=1.63.0" "grpcio-tools>=1.63.0"
RUN git clone --depth 1 https://github.com/ciromattia/kcc.git /opt/kcc
RUN pip install --no-cache-dir -r /opt/kcc/requirements.txt
COPY worker-kcc/ /opt/kcc-grpc/
RUN python -m grpc_tools.protoc \
    -I /opt/kcc-grpc/proto \
    --python_out=/opt/kcc-grpc \
    --grpc_python_out=/opt/kcc-grpc \
    /opt/kcc-grpc/proto/conversion.proto

# ─────────────────────────────────────────────────────────────
# Stage 4: Final single-container image
# ─────────────────────────────────────────────────────────────
FROM python:3.11-slim-bullseye

# System packages: Node 20, nginx, redis, supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg \
    libgl1 libfreetype6 libfontconfig1 p7zip-full openssl \
    nginx redis-server supervisor \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Python venv + KCC
COPY --from=python-builder /opt/venv /opt/venv
COPY --from=python-builder /opt/kcc /opt/kcc
COPY --from=python-builder /opt/kcc-grpc /opt/kcc-grpc

# NestJS API + Worker
WORKDIR /app
COPY --from=node-builder /app/node_modules ./node_modules
COPY --from=node-builder /app/apps/api/dist ./apps/api/dist
COPY --from=node-builder /app/apps/worker/dist ./apps/worker/dist
COPY --from=node-builder /app/packages ./packages
COPY --from=node-builder /app/worker-kcc/proto ./worker-kcc/proto
COPY apps/api/package.json ./apps/api/package.json
COPY apps/worker/package.json ./apps/worker/package.json

# Frontend
COPY --from=frontend-builder /build/dist /usr/share/nginx/html

# Config
COPY infra/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY infra/docker/supervisord.conf /etc/supervisor/conf.d/mgc.conf
COPY infra/docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && rm -f /etc/nginx/sites-enabled/default

RUN mkdir -p /data/files/input /data/files/output /var/log/mgc

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/opt/kcc-grpc:/opt/kcc"
ENV KCC_SCRIPT="/opt/kcc/kcc-c2e.py"
ENV GRPC_PORT="50051"
ENV NODE_ENV="production"
ENV REDIS_URL="redis://localhost:6379"
ENV DATABASE_URL="file:/data/mgc.db"
ENV STORAGE_PATH="/data/files"
ENV PORT="3000"
ENV KCC_GRPC_ADDR="localhost:50051"

VOLUME ["/data"]
EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
