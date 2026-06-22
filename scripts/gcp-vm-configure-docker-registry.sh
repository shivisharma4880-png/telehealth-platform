#!/usr/bin/env bash
# Run on the Compute Engine VM as the same Linux user that runs docker compose.
# Registers the gcloud credential helper for Artifact Registry.
#
# Usage:
#   GCP_REGION=asia-south1 bash scripts/gcp-vm-configure-docker-registry.sh
#
set -euo pipefail
GCP_REGION="${GCP_REGION:-asia-south1}"

if ! command -v gcloud &>/dev/null; then
  echo "gcloud not found. Install Google Cloud SDK or run: bash scripts/gcp-vm-bootstrap.sh" >&2
  exit 1
fi

echo "Configuring Docker for ${GCP_REGION}-docker.pkg.dev ..."
gcloud auth configure-docker "${GCP_REGION}-docker.pkg.dev" --quiet

GCP_PROJECT_ID="${GCP_PROJECT_ID:-tele-health-495910}"
echo "Test pull (optional):"
echo "  docker pull ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/telehealth/backend:latest"
