# AI-Powered Telehealth Platform MVP

A full-stack, AI-assisted teleconsultation platform for outpatient care. Covers the complete patient journey: **booking → consult (clinician workspace + AI voice) → AI SOAP notes → e-prescription**.

## Features

- **Patient Portal** – OTP sign-up, provider discovery, slot booking, pre-consult questionnaire, AI voice consult, prescription download
- **Clinician Console** – Schedule management, live transcription (OpenAI Whisper), AI-drafted SOAP notes (GPT-4o), e-prescription with drug interaction checks
- **Admin Console** – Clinic management, scheduling, appointment dashboard, CSV export
- **AI Pipeline** – Real-time audio → Whisper → SSE transcript stream → GPT-4o → editable SOAP note
- **E-Prescription** – Drug formulary, interaction/allergy checks, ReportLab PDF with digital signature
- **Security** – JWT RBAC, PHI encryption, append-only audit logs, DPDP-aligned consent flows

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui |
| Backend | Python FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2 |
| Database | PostgreSQL 15 (FHIR R4-inspired schema) |
| Voice AI (patient) | Groq STT / LLM / TTS |
| ASR | OpenAI Whisper API |
| LLM | OpenAI GPT-4o |
| PDF | ReportLab |
| Auth | JWT (access 15m + refresh 7d), bcrypt |
| Payments | Razorpay (mock stub for MVP) |

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+
- Python 3.11+

### 1. Clone and configure
```bash
git clone <repo-url>
cd telehealth-platform
cp .env.example .env
# Edit .env — at minimum set OPENAI_API_KEY; add GROQ_API_KEY for the patient voice consult demo
```

### 2. Start with Docker Compose
```bash
docker-compose up --build
```

This starts:
- PostgreSQL on port 5433 (host; mapped from container 5432)
- FastAPI backend on http://localhost:8001 (host port; container still listens on 8000)
- Next.js frontend on http://localhost:3000

If you run the API with `uvicorn` directly instead of Docker, use `--port 8001` (or any free port) and set `NEXT_PUBLIC_API_URL` to match, so you do not hit another service that may already be bound to 8000.

### 3. Run DB migrations and seed data
```bash
docker-compose exec backend alembic upgrade head
docker-compose exec backend python -m app.seed
```

### 4. Access the app
- **Patient Portal**: http://localhost:3000
- **Clinician Console**: http://localhost:3000/clinician
- **Admin Console**: http://localhost:3000/admin
- **API Docs**: http://localhost:8001/docs

## Development

### Backend (FastAPI)
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8001
```

### Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev
```

## Seed Accounts

After running `python -m app.seed`:

| Role | Email/Phone | Password/OTP |
|------|-------------|--------------|
| Admin | admin@clinic.com | admin123 |
| Clinician | dr.patel@clinic.com | doctor123 |
| Patient | +91-9876543210 | OTP: 123456 (mock) |

## Architecture

```
telehealth-platform/
├── frontend/               # Next.js 14 App Router
│   ├── app/
│   │   ├── (patient)/      # Booking, consult, records
│   │   ├── (clinician)/    # Dashboard, consult room, prescriptions
│   │   ├── (admin)/        # Clinic management, reports
│   │   └── api/            # Auth proxy API routes
│   ├── components/         # Reusable UI components
│   └── lib/                # API client, hooks, utilities
├── backend/                # Python FastAPI
│   ├── app/
│   │   ├── api/            # Route handlers
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   └── core/           # Config, security, database
│   └── alembic/            # DB migrations
└── docker-compose.yml
```

## Compliance Notes

- PHI stored in PostgreSQL with column-level encryption annotations
- All key events logged to append-only `audit_events` table
- Consent text versioned per DPDP Act requirements
- AI outputs (SOAP notes) clearly labeled as drafts requiring clinician approval
- Prescriptions require explicit clinician sign-off before generation
