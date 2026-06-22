#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────
#  Telehealth Platform – One-command startup script
# ─────────────────────────────────────────────────────────
PLATFORM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PLATFORM_DIR"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[telehealth]${NC} $*"; }
warn()    { echo -e "${YELLOW}[telehealth]${NC} $*"; }
error()   { echo -e "${RED}[telehealth]${NC} $*" >&2; exit 1; }

# ── Pre-flight checks ──────────────────────────────────
command -v docker >/dev/null 2>&1 || error "Docker not found. Install Docker Desktop first."
docker info >/dev/null 2>&1      || error "Docker daemon is not running. Start Docker Desktop."
(docker compose version >/dev/null 2>&1 || docker-compose --version >/dev/null 2>&1) \
  || error "Docker Compose not found."

COMPOSE="docker compose"
$COMPOSE version >/dev/null 2>&1 || COMPOSE="docker-compose"

# ── Environment file ──────────────────────────────────
if [ ! -f .env ]; then
  warn ".env not found — creating from .env.example"
  cp .env.example .env
  warn "Edit .env and add your OPENAI_API_KEY (and GROQ_API_KEY for voice consult), then re-run."
fi

# Source .env for local info messages
set -o allexport; source .env 2>/dev/null || true; set +o allexport

# ── Build + Start services ────────────────────────────
info "Building and starting all services (db + backend + frontend)…"
$COMPOSE up --build -d

# ── Wait for Postgres ─────────────────────────────────
info "Waiting for PostgreSQL to be ready…"
for i in $(seq 1 30); do
  if $COMPOSE exec -T db pg_isready -U telehealth -d telehealth_db >/dev/null 2>&1; then
    info "PostgreSQL is ready."
    break
  fi
  sleep 2
  [ "$i" -eq 30 ] && error "PostgreSQL did not become ready in time."
done

# ── Run Alembic migrations ────────────────────────────
info "Running database migrations…"
$COMPOSE exec -T backend alembic upgrade head

# ── Seed data ────────────────────────────────────────
info "Seeding initial data (admin, demo clinician, demo patient, slots)…"
$COMPOSE exec -T backend python -m app.seed && info "Seed complete." \
  || warn "Seed script returned non-zero (may already be seeded — that's OK)."

# ── Health check ─────────────────────────────────────
info "Checking backend health…"
for i in $(seq 1 15); do
  STATUS=$(curl -sf http://localhost:8001/health 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null || true)
  if [ "$STATUS" = "healthy" ]; then
    break
  fi
  sleep 2
  [ "$i" -eq 15 ] && warn "Backend health check timed out. Check logs: docker compose logs backend"
done

# ── Done ─────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       Telehealth Platform is UP!                        ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Frontend   →  http://localhost:3000                    ║${NC}"
echo -e "${GREEN}║  API        →  http://localhost:8001                    ║${NC}"
echo -e "${GREEN}║  API Docs   →  http://localhost:8001/docs               ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Demo accounts                                          ║${NC}"
echo -e "${GREEN}║  Admin     →  admin@clinic.com        / admin123        ║${NC}"
echo -e "${GREEN}║  Clinician →  dr.patel@clinic.com     / doctor123       ║${NC}"
echo -e "${GREEN}║  Patient   →  OTP login → phone +919876543210           ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
info "View logs:    docker compose logs -f"
info "Stop:         docker compose down"
info "Wipe data:    docker compose down -v"
