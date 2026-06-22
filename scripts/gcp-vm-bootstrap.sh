#!/usr/bin/env bash
# Run on the Compute Engine VM (Ubuntu) once: Docker Engine + Compose plugin,
# Google Cloud CLI + Artifact Registry docker auth (uses VM service account).
#
# Usage on VM:
#   curl -fsSL ... | bash   # or copy repo and: bash scripts/gcp-vm-bootstrap.sh
#
# Optional env: GCP_REGION (default asia-south1)

set -euo pipefail

GCP_REGION="${GCP_REGION:-asia-south1}"

if [[ "$(id -u)" -eq 0 ]]; then
  SUDO=""
else
  SUDO="sudo"
fi

echo "Installing Docker..."
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | $SUDO sh
fi

$SUDO usermod -aG docker "${USER}" || true

echo "Installing Google Cloud CLI..."
if ! command -v gcloud &>/dev/null; then
  export DEBIAN_FRONTEND=noninteractive
  $SUDO apt-get update -qq
  $SUDO apt-get install -y -qq apt-transport-https ca-certificates curl gnupg
  curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg |
    $SUDO gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
  echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" |
    $SUDO tee /etc/apt/sources.list.d/google-cloud-sdk.list >/dev/null
  $SUDO apt-get update -qq
  $SUDO apt-get install -y -qq google-cloud-cli
fi

echo "Configuring Docker credential helper for Artifact Registry..."
gcloud auth configure-docker "${GCP_REGION}-docker.pkg.dev" --quiet

echo "If you run compose with sudo later, copy cred helpers for root:"
echo "  sudo mkdir -p /root/.docker && sudo cp \"\$HOME/.docker/config.json\" /root/.docker/config.json"

echo "Done. Log out and back in (or newgrp docker) if docker permission denied."
echo "Then clone this repo on the VM, set env vars, and run:"
echo "  bash scripts/gcp-vm-run-stack.sh"
