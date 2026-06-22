#!/usr/bin/env bash
# Run on your laptop (gcloud logged in as project Owner/Editor). Grants the VM's
# attached service account permission to pull images from Artifact Registry.
#
# Usage:
#   GCP_PROJECT_ID=tele-health-495910 INSTANCE_NAME=telehealth-vm ZONE=asia-south1-a \
#     bash scripts/gcp-grant-vm-artifact-registry-reader.sh
#
set -euo pipefail
: "${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
: "${INSTANCE_NAME:?Set INSTANCE_NAME (e.g. telehealth-vm)}"
: "${ZONE:?Set ZONE (e.g. asia-south1-a)}"

VM_SA="$(gcloud compute instances describe "${INSTANCE_NAME}" \
  --zone="${ZONE}" \
  --project="${GCP_PROJECT_ID}" \
  --format='get(serviceAccounts[0].email)')"

echo "VM service account: ${VM_SA}"
echo "Granting roles/artifactregistry.reader on project ${GCP_PROJECT_ID}..."

gcloud projects add-iam-policy-binding "${GCP_PROJECT_ID}" \
  --member="serviceAccount:${VM_SA}" \
  --role="roles/artifactregistry.reader" \
  --quiet

echo "Done. On the VM, run: bash scripts/gcp-vm-configure-docker-registry.sh"
echo "Then retry: bash scripts/gcp-vm-run-stack.sh"
