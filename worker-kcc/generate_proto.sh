#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python -m grpc_tools.protoc \
  -I proto \
  --python_out=. \
  --grpc_python_out=. \
  proto/conversion.proto
