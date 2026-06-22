#!/usr/bin/env bash
# Build backend + frontend and push to Artifact Registry.
#
# Required env: GCP_PROJECT_ID, NEXT_PUBLIC_API_URL (public URL of API for browser)
# Optional: GCP_REGION (default asia-south1), AR_REPO (default telehealth),
#           IMAGE_TAG (default git short SHA or 'latest')

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

: "${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
: "${NEXT_PUBLIC_API_URL:?Set NEXT_PUBLIC_API_URL e.g. http://EXTERNAL_IP:8000}"

GCP_REGION="${GCP_REGION:-asia-south1}"
AR_REPO="${AR_REPO:-telehealth}"
IMAGE_TAG="${IMAGE_TAG:-$(git -C "${ROOT}" rev-parse --short HEAD 2>/dev/null || echo latest)}"
REGISTRY="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${AR_REPO}"

if ! command -v gcloud &>/dev/null; then
  echo "gcloud not found. Install Google Cloud SDK and ensure it is on PATH." >&2
  exit 1
fi

if ! command -v docker &>/dev/null; then
  echo "docker not found." >&2
  exit 1
fi

gcloud auth configure-docker "${GCP_REGION}-docker.pkg.dev" --quiet

BACKEND_REF="${REGISTRY}/backend:${IMAGE_TAG}"
FRONTEND_REF="${REGISTRY}/frontend:${IMAGE_TAG}"

DOCKER_PLATFORM="${DOCKER_PLATFORM:-linux/amd64}"

echo "Building ${BACKEND_REF} (${DOCKER_PLATFORM})"
docker build --platform "${DOCKER_PLATFORM}" -t "${BACKEND_REF}" -f "${ROOT}/backend/Dockerfile" "${ROOT}/backend"

echo "Building ${FRONTEND_REF} (NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}) (${DOCKER_PLATFORM})"
docker build --platform "${DOCKER_PLATFORM}" -t "${FRONTEND_REF}" \
  --build-arg NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL}" \
  -f "${ROOT}/frontend/Dockerfile" "${ROOT}/frontend"

echo "Pushing..."
docker push "${BACKEND_REF}"
docker push "${FRONTEND_REF}"

echo "Set on the VM:"
echo "  export BACKEND_IMAGE=${BACKEND_REF}"
echo "  export FRONTEND_IMAGE=${FRONTEND_REF}"
