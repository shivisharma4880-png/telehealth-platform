#!/usr/bin/env bash
# On the VM (after gcp-vm-bootstrap.sh): pull images and start production compose.
#
# External Postgres (default):
#   Requires: BACKEND_IMAGE, FRONTEND_IMAGE, DATABASE_URL, JWT_SECRET,
#   JWT_REFRESH_SECRET, ALLOWED_ORIGINS, NEXTAUTH_SECRET, NEXTAUTH_URL
#   Merge: docker-compose.prod.yml + docker-compose.external-db.yml (+ optional caddy / overrides).
#
# Bundled Postgres on this VM:
#   USE_GCP_VM_OVERRIDE=1 and POSTGRES_PASSWORD (DATABASE_URL comes from docker-compose.gcp-vm.override.yml).
#
# Optional: COMPOSE_FILE (default: repo-root docker-compose.prod.yml).
# Optional: USE_CADDY=1 — also merge docker-compose.caddy.yml (HTTPS on 80/443).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Flat deploy dir on VM (compose + scripts in same folder) vs full repo clone.
if [[ -f "${SCRIPT_DIR}/docker-compose.prod.yml" ]]; then
  ROOT="${SCRIPT_DIR}"
else
  ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
fi
COMPOSE_FILE="${COMPOSE_FILE:-${ROOT}/docker-compose.prod.yml}"
OVERRIDE_FILE="${ROOT}/docker-compose.gcp-vm.override.yml"
CADDY_FILE="${ROOT}/docker-compose.caddy.yml"

: "${BACKEND_IMAGE:?}"
: "${FRONTEND_IMAGE:?}"

if [[ "${USE_GCP_VM_OVERRIDE:-}" == "1" ]]; then
  : "${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD when USE_GCP_VM_OVERRIDE=1}"
  if [[ ! -f "${OVERRIDE_FILE}" ]]; then
    echo "Missing ${OVERRIDE_FILE}" >&2
    exit 1
  fi
fi

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "Missing ${COMPOSE_FILE}. Clone the repo or set COMPOSE_FILE." >&2
  exit 1
fi

compose_files=( -f "${COMPOSE_FILE}" )
if [[ "${USE_GCP_VM_OVERRIDE:-}" == "1" ]]; then
  compose_files+=( -f "${OVERRIDE_FILE}" )
fi
if [[ "${USE_CADDY:-}" == "1" ]]; then
  if [[ ! -f "${CADDY_FILE}" ]]; then
    echo "USE_CADDY=1 but missing ${CADDY_FILE}" >&2
    exit 1
  fi
  compose_files+=( -f "${CADDY_FILE}" )
fi

# Stop prior project containers so host ports (e.g. legacy 3000/8000 publish) are freed.
docker compose "${compose_files[@]}" down --remove-orphans 2>/dev/null || true

docker compose "${compose_files[@]}" pull
docker compose "${compose_files[@]}" up -d
