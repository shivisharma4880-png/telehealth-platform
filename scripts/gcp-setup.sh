#!/usr/bin/env bash
# One-time GCP setup: APIs, Artifact Registry repo, VM puller service account,
# optional e2-micro VM + firewall (telehealth-server tag).
#
# Required: gcloud authenticated (`gcloud auth login`), billing enabled.
# Required env: GCP_PROJECT_ID
# Optional: GCP_REGION (default asia-south1), AR_REPO (default telehealth),
#           GCP_ZONE (default ${GCP_REGION}-a), INSTANCE_NAME (default telehealth-vm),
#           CREATE_VM=1 to provision a VM.
#
# Always Free: Google’s month-long e2-micro credit applies only in select US regions
# (e.g. us-central1, us-west1, us-east1). asia-south1 is usually billed at on-demand
# e2-micro rates (still small); use a US region if you need Always Free Compute.

set -euo pipefail

: "${GCP_PROJECT_ID:?Set GCP_PROJECT_ID to your Google Cloud project ID}"

GCP_REGION="${GCP_REGION:-asia-south1}"
AR_REPO="${AR_REPO:-telehealth}"
GCP_ZONE="${GCP_ZONE:-${GCP_REGION}-a}"
INSTANCE_NAME="${INSTANCE_NAME:-telehealth-vm}"
SA_ID="telehealth-vm-puller"
SA_EMAIL="${SA_ID}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
NETWORK_TAG="telehealth-server"

if ! command -v gcloud &>/dev/null; then
  echo "gcloud not found. Install Google Cloud SDK and ensure it is on PATH." >&2
  exit 1
fi

gcloud config set project "${GCP_PROJECT_ID}"

ALWAYS_FREE_REGIONS_REGEX='^(us-central1|us-west1|us-east1)$'
if [[ ! "${GCP_REGION}" =~ ${ALWAYS_FREE_REGIONS_REGEX} ]]; then
  echo "Note: e2-micro Always Free Compute (when offered) is limited to certain US regions;" >&2
  echo "      ${GCP_REGION} may incur normal e2-micro pricing. See cloud.google.com/free" >&2
fi

echo "Enabling APIs..."
gcloud services enable \
  artifactregistry.googleapis.com \
  compute.googleapis.com \
  iam.googleapis.com \
  --project="${GCP_PROJECT_ID}"

echo "Creating Artifact Registry Docker repo '${AR_REPO}' in ${GCP_REGION} (if missing)..."
if ! gcloud artifacts repositories describe "${AR_REPO}" --location="${GCP_REGION}" &>/dev/null; then
  gcloud artifacts repositories create "${AR_REPO}" \
    --repository-format=docker \
    --location="${GCP_REGION}" \
    --description="Telehealth containers"
fi

echo "Service account for VM image pulls: ${SA_EMAIL}"
if ! gcloud iam service-accounts describe "${SA_EMAIL}" --project="${GCP_PROJECT_ID}" &>/dev/null; then
  gcloud iam service-accounts create "${SA_ID}" \
    --project="${GCP_PROJECT_ID}" \
    --display-name="Telehealth VM Artifact Registry reader"
fi

gcloud projects add-iam-policy-binding "${GCP_PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/artifactregistry.reader" \
  >/dev/null

echo "Docker credential helper for local pushes (quiet):"
gcloud auth configure-docker "${GCP_REGION}-docker.pkg.dev" --quiet

if [[ "${CREATE_VM:-}" == "1" ]]; then
  echo "Firewall rule for SSH + app ports (idempotent name)..."
  if ! gcloud compute firewall-rules describe allow-telehealth-app --project="${GCP_PROJECT_ID}" &>/dev/null; then
    gcloud compute firewall-rules create allow-telehealth-app \
      --project="${GCP_PROJECT_ID}" \
      --direction=INGRESS \
      --priority=1000 \
      --network=default \
      --action=ALLOW \
      --rules=tcp:22,tcp:80,tcp:443 \
      --source-ranges=0.0.0.0/0 \
      --target-tags="${NETWORK_TAG}"
  fi

  echo "Creating VM ${INSTANCE_NAME} (if not exists)..."
  if gcloud compute instances describe "${INSTANCE_NAME}" --zone="${GCP_ZONE}" --project="${GCP_PROJECT_ID}" &>/dev/null; then
    echo "Instance ${INSTANCE_NAME} already exists in ${GCP_ZONE}."
  else
    gcloud compute instances create "${INSTANCE_NAME}" \
      --project="${GCP_PROJECT_ID}" \
      --zone="${GCP_ZONE}" \
      --machine-type=e2-micro \
      --network-interface=network-tier=PREMIUM,subnet=default \
      --maintenance-policy=MIGRATE \
      --provisioning-model=STANDARD \
      --service-account="${SA_EMAIL}" \
      --scopes=https://www.googleapis.com/auth/cloud-platform \
      --tags="${NETWORK_TAG}" \
      --image-family=ubuntu-2204-lts \
      --image-project=ubuntu-os-cloud \
      --boot-disk-size=20GB \
      --boot-disk-type=pd-balanced \
      --labels=app=telehealth \
      --reservation-affinity=any
    echo "VM created. SSH: gcloud compute ssh ${INSTANCE_NAME} --zone=${GCP_ZONE}"
  fi
fi

echo "Done."
echo "Registry: ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${AR_REPO}"
echo "Push images: scripts/gcp-push-images.sh"
echo "On VM (after SSH): bash scripts/gcp-vm-bootstrap.sh"
