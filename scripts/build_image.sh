#!/usr/bin/env bash
set -euo pipefail

# Build and optionally push the Docker image for mgc-foss
# Defaults build the production image locally for the current arch.

# Determine repo root based on this script's location so the script
# works from any current working directory.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

CTX="${REPO_ROOT}"
FILE="${REPO_ROOT}/Dockerfile.prod"
PLATFORM=""
PUSH="false"
TAGS=()
BUILD_ARGS=("NEXT_PUBLIC_API_URL=/api" "NEXT_PUBLIC_MAX_FILES=10")

usage() {
  echo "Usage: $0 [--context DIR] [--file DOCKERFILE] [--platform PLATFORM] [--push] [--tag NAME:TAG] [--build-arg KEY=VALUE]..." >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --context)
      CTX="$2"; shift 2;;
    --file)
      FILE="$2"; shift 2;;
    --platform)
      PLATFORM="$2"; shift 2;;
    --push)
      PUSH="true"; shift;;
    --tag)
      TAGS+=("$2"); shift 2;;
    --build-arg)
      BUILD_ARGS+=("$2"); shift 2;;
    -h|--help)
      usage; exit 0;;
    *)
      echo "Unknown argument: $1" >&2; usage; exit 1;;
  esac
done

if [[ ${#TAGS[@]} -eq 0 ]]; then
  # Default local tag based on short SHA if available
  if git rev-parse --short HEAD >/dev/null 2>&1; then
    SHORT_SHA=$(git rev-parse --short HEAD)
  else
    SHORT_SHA="local"
  fi
  TAGS=("nilsleo/kcc-web:${SHORT_SHA}")
fi

echo "Context: $CTX"
echo "Dockerfile: $FILE"
[[ -n "$PLATFORM" ]] && echo "Platform: $PLATFORM" || echo "Platform: (host default)"
echo "Push: $PUSH"
echo "Tags: ${TAGS[*]}"
echo "Build args: ${BUILD_ARGS[*]}"

BUILDX_AVAILABLE=false
if docker buildx version >/dev/null 2>&1; then
  BUILDX_AVAILABLE=true
fi

if [[ -n "$PLATFORM" ]]; then
  if [[ "$BUILDX_AVAILABLE" != true ]]; then
    echo "docker buildx not available but --platform specified. Install Buildx or omit --platform." >&2
    exit 1
  fi
  # Use buildx
  ARGS=("buildx" "build" "--file" "$FILE" "--platform" "$PLATFORM" "$CTX")
  for t in "${TAGS[@]}"; do ARGS+=("--tag" "$t"); done
  for ba in "${BUILD_ARGS[@]}"; do ARGS+=("--build-arg" "$ba"); done
  if [[ "$PUSH" == "true" ]]; then
    ARGS+=("--push")
  else
    # load into local docker if single-arch platform
    ARGS+=("--load")
  fi
  echo "+ docker ${ARGS[*]}"
  docker "${ARGS[@]}"
else
  # Plain docker build for host arch
  ARGS=("build" "-f" "$FILE")
  for t in "${TAGS[@]}"; do ARGS+=("-t" "$t"); done
  for ba in "${BUILD_ARGS[@]}"; do ARGS+=("--build-arg" "$ba"); done
  ARGS+=("$CTX")
  echo "+ docker ${ARGS[*]}"
  docker "${ARGS[@]}"

  if [[ "$PUSH" == "true" ]]; then
    for t in "${TAGS[@]}"; do
      echo "+ docker push $t"
      docker push "$t"
    done
  fi
fi

echo "Done."
