# STAGE 1: BUILDER
FROM python:3.13-slim-bullseye AS builder

RUN set -x && \
    BUILD_DEPS="build-essential cmake libffi-dev libfreetype6-dev libfontconfig1-dev libpng-dev libjpeg-dev libssl-dev libxft-dev make python3-dev" && \
    RUNTIME_DEPS="bash ca-certificates curl unzip chrpath locales locales-all libfreetype6 libfontconfig1 p7zip-full python3 python3-pip libgl1" && \
    DEBIAN_FRONTEND=noninteractive apt-get update -y && \
    apt-get install -y --no-install-recommends ${BUILD_DEPS} ${RUNTIME_DEPS}

RUN python -m venv /opt/venv && \
    . /opt/venv/bin/activate && \
    pip install --upgrade pip

# Heavy deps compiled separately for layer caching
RUN . /opt/venv/bin/activate && pip install --no-cache-dir numpy==2.3.4
RUN . /opt/venv/bin/activate && pip install --no-cache-dir PyMuPDF==1.26.6

COPY requirements-docker.txt /tmp/requirements-docker.txt
RUN . /opt/venv/bin/activate && pip install --no-cache-dir -r /tmp/requirements-docker.txt

# Install gRPC
COPY requirements.txt /tmp/requirements.txt
RUN . /opt/venv/bin/activate && pip install --no-cache-dir -r /tmp/requirements.txt

# Copy KCC source and generate proto stubs
COPY . /opt/kcc-grpc/
COPY --from=kcc /opt/kcc/ /opt/kcc/
# Note: in practice build KCC from context; here we assume kcc source is included
# via build-arg or the image is extended. For standalone dev builds, KCC source
# should be placed at /opt/kcc/ before this step.

# Generate gRPC stubs
RUN . /opt/venv/bin/activate && \
    python -m grpc_tools.protoc \
      -I /opt/kcc-grpc/proto \
      --python_out=/opt/kcc-grpc \
      --grpc_python_out=/opt/kcc-grpc \
      /opt/kcc-grpc/proto/conversion.proto

# STAGE 2: FINAL
FROM python:3.13-slim-bullseye

# i386 support for kindlegen (32-bit binary)
RUN dpkg --add-architecture i386 && \
    DEBIAN_FRONTEND=noninteractive apt-get update && \
    apt-get install -y --no-install-recommends \
        libc6-i386 lib32stdc++6 \
        bash ca-certificates curl unzip p7zip-full libfreetype6 libfontconfig1 libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /opt/kcc-grpc /opt/kcc-grpc
COPY --from=builder /opt/kcc /opt/kcc

# Download kindlegen (32-bit Linux binary)
RUN mkdir -p /opt/kcc/kindlegen && \
    curl -L "https://ia601302.us.archive.org/zip_dir.php?path=/11/items/kindlegen.zip" \
         -o /tmp/kindlegen_all.zip && \
    unzip /tmp/kindlegen_all.zip kindlegen -d /tmp/kindlegen_extracted && \
    cp /tmp/kindlegen_extracted/kindlegen /opt/kcc/kindlegen/kindlegen && \
    chmod +x /opt/kcc/kindlegen/kindlegen && \
    rm -rf /tmp/kindlegen_all.zip /tmp/kindlegen_extracted

RUN ln -s /opt/kcc/kindlegen/kindlegen /usr/local/bin/kindlegen

ENV PATH="/opt/venv/bin:/opt/kcc:$PATH"
ENV KCC_SCRIPT="/opt/kcc/kcc-c2e.py"
ENV GRPC_PORT="50051"
ENV PYTHONPATH="/opt/kcc-grpc:/opt/kcc"

WORKDIR /opt/kcc-grpc

EXPOSE 50051

CMD ["python", "server.py"]
