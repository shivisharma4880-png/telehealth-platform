"""PDF attachment for completed AI voice consult (patient download)."""

from __future__ import annotations

import logging
import os
import secrets
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.appointment import Appointment
from app.models.medication import Prescription
from app.models.organization import Organization
from app.models.patient import Patient
from app.models.practitioner import Practitioner
from app.models.user import User
from app.models.voice_consult_session import VoiceConsultSession
from app.services.groq_voice_service import _fallback_pdf_fields, groq_voice_service
from app.services.pdf_service import generate_ai_voice_visit_summary_pdf

logger = logging.getLogger(__name__)


def _messages_to_conversation_text(messages: list) -> str:
    lines: list[str] = []
    for m in messages or []:
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if role not in ("user", "assistant") or not content:
            continue
        label = "Patient" if role == "user" else "Assistant"
        lines.append(f"{label}: {content}")
    return "\n".join(lines)


async def attach_ai_visit_summary_pdf(
    db: AsyncSession,
    *,
    session: VoiceConsultSession,
    patient: Patient,
) -> str | None:
    """
    Build PDF from conversation + LLM fields; set pdf_token on the AI consult prescription.
    Returns the download token, or None if skipped/failed.
    """
    result = await db.execute(
        select(Prescription).where(Prescription.voice_consult_session_id == session.id)
    )
    prescription = result.scalar_one_or_none()
    if not prescription:
        logger.warning("No prescription row for voice session %s; skip PDF", session.id)
        return None
    if prescription.pdf_path and prescription.pdf_token:
        return prescription.pdf_token

    conversation = _messages_to_conversation_text(session.messages or [])
    final_hint = session.final_result if isinstance(session.final_result, dict) else None

    if groq_voice_service.is_configured():
        try:
            fields = await groq_voice_service.pdf_document_payload(conversation, final_hint)
        except Exception as e:
            logger.exception("PDF LLM step failed: %s", e)
            fields = _fallback_pdf_fields(final_hint)
    else:
        fields = _fallback_pdf_fields(final_hint)

    org_data = {"name": "Telehealth Platform", "address": "", "phone": ""}
    booked_clinician: str | None = None
    chief_complaint: str | None = None
    aid = getattr(session, "appointment_id", None)
    if aid:
        appt = await db.get(Appointment, aid)
        if appt:
            chief_complaint = (appt.chief_complaint or "").strip() or None
            prac = await db.get(Practitioner, appt.practitioner_id)
            if prac:
                booked_clinician = prac.full_name
                if prac.organization_id:
                    org = await db.get(Organization, prac.organization_id)
                    if org:
                        org_data = {
                            "name": org.name or "Medical Clinic",
                            "address": org.address or "",
                            "phone": org.phone or "",
                        }

    patient_user = await db.get(User, patient.user_id)

    age = "N/A"
    if patient.date_of_birth:
        today = datetime.now().date()
        age = str(today.year - patient.date_of_birth.year)
    dob_str = "-"
    if patient.date_of_birth:
        dob_str = patient.date_of_birth.strftime("%d/%m/%Y")

    patient_data = {
        "full_name": patient.full_name or "Unknown",
        "age": age,
        "gender": patient.gender.value if patient.gender else "N/A",
        "phone": (patient_user.phone if patient_user and patient_user.phone else None) or "-",
        "date_of_birth": dob_str,
        "mrn": patient.id.replace("-", "")[:16].upper(),
        "address": "-",
    }

    visit_datetime_display = datetime.now(timezone.utc).strftime("%d/%m/%Y %I:%M %p UTC")
    session_ref = session.id.replace("-", "")[:14].upper()

    os.makedirs(settings.pdf_storage_path, exist_ok=True)
    filename = f"ai_visit_{session.id}_{uuid.uuid4().hex[:8]}.pdf"
    filepath = os.path.join(settings.pdf_storage_path, filename)

    try:
        generate_ai_voice_visit_summary_pdf(
            organization_data=org_data,
            patient_data=patient_data,
            visit_datetime_display=visit_datetime_display,
            booked_clinician=booked_clinician,
            chief_complaint=chief_complaint,
            session_ref=session_ref,
            visit_summary=fields.get("visit_summary") or "",
            prescription_section=fields.get("prescription_section") or "",
            safety_disclaimer=fields.get("safety_disclaimer") or "",
            filepath=filepath,
        )
    except Exception as e:
        logger.exception("AI visit PDF render failed: %s", e)
        return None

    token = secrets.token_hex(32)
    prescription.pdf_path = filepath
    prescription.pdf_token = token
    prescription.pdf_token_expires_at = datetime.now(timezone.utc) + timedelta(days=14)
    await db.flush()

    logger.info("AI visit summary PDF attached session=%s prescription=%s", session.id, prescription.id)
    return token
