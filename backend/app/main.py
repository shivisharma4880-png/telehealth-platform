import os
import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.bootstrap_admin import ensure_platform_admin
from app.api import auth, patients, practitioners, appointments, encounters, prescriptions, admin, consent, audio_consult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Telehealth Platform API...")
    os.makedirs(settings.pdf_storage_path, exist_ok=True)
    try:
        async with AsyncSessionLocal() as db:
            await ensure_platform_admin(db)
            await db.commit()
    except Exception:
        logger.exception(
            "Could not ensure platform bootstrap admin (database may be unreachable at startup); "
            "admin will be created on the next successful startup."
        )
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Telehealth Platform API",
    description="""
    ## AI-Powered Teleconsultation Platform

    Complete REST API for:
    - **Patient** booking, consultation, and records management
    - **Clinician** schedule, AI-assisted notes, and e-prescriptions
    - **Admin** clinic management and reporting

    ### AI Features
    - Real-time audio transcription (OpenAI Whisper)
    - SOAP note generation (GPT-4o)
    - Groq voice consult (Whisper-class STT + Llama + Groq TTS on same key)

    ### Compliance
    - HIPAA-aligned security practices
    - India DPDP Act consent flows
    - Telemedicine Practice Guidelines 2020 compliant
    - Append-only audit logs
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(patients.router, prefix="/api/v1")
app.include_router(practitioners.router, prefix="/api/v1")
app.include_router(appointments.router, prefix="/api/v1")
app.include_router(encounters.router, prefix="/api/v1")
app.include_router(prescriptions.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(consent.router, prefix="/api/v1")
app.include_router(audio_consult.router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.environment,
        "ai_enabled": bool(settings.openai_api_key),
        "groq_voice_enabled": bool(settings.groq_api_key),
    }


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "AI-Powered Telehealth Platform API",
        "docs": "/docs",
        "health": "/health",
    }
