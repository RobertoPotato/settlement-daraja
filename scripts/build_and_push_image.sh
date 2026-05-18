#!/usr/bin/env bash

set -euo pipefail

# Update these constants for your private registry.
REPO_URL="registry.alphasystems.co.ke"
IMAGE_NAME="settlement-mpesa-service"
DOCKERFILE_PATH="Dockerfile"
BUILD_CONTEXT="."

usage() {
  echo "Usage: $0 <tag1> [tag2 ...]"
  echo "Example: $0 v1.0.0 latest"
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

FULL_IMAGE="${REPO_URL}/${IMAGE_NAME}"
PRIMARY_TAG="$1"

echo "Building ${FULL_IMAGE}:${PRIMARY_TAG}..."
docker build -f "${DOCKERFILE_PATH}" -t "${FULL_IMAGE}:${PRIMARY_TAG}" "${BUILD_CONTEXT}"

for tag in "$@"; do
  if [[ "${tag}" != "${PRIMARY_TAG}" ]]; then
    echo "Tagging ${FULL_IMAGE}:${PRIMARY_TAG} as ${FULL_IMAGE}:${tag}..."
    docker tag "${FULL_IMAGE}:${PRIMARY_TAG}" "${FULL_IMAGE}:${tag}"
  fi
done

for tag in "$@"; do
  echo "Pushing ${FULL_IMAGE}:${tag}..."
  docker push "${FULL_IMAGE}:${tag}"
done

echo "Done."
echo "Set APP_IMAGE=${FULL_IMAGE}:${PRIMARY_TAG} when deploying with docker-compose.prod.yaml"