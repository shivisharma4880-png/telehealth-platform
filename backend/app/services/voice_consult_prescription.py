"""Persist a patient-visible prescription row when an AI voice consult completes."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medication import MedicationRequest, Prescription
from app.models.patient import Patient
from app.models.appointment import Appointment
from app.models.practitioner import Practitioner
from app.models.voice_consult_session import VoiceConsultSession, VoiceConsultSessionStatus
from app.services.audit_service import log_event


async def ensure_prescription_for_voice_session(
    db: AsyncSession,
    *,
    session: VoiceConsultSession,
    patient: Patient,
) -> None:
    if session.status != VoiceConsultSessionStatus.COMPLETED:
        return
    existing = await db.execute(
        select(Prescription).where(Prescription.voice_consult_session_id == session.id)
    )
    if existing.scalar_one_or_none():
        return

    fr = session.final_result or {}
    summary = (fr.get("summary") or "").strip()
    assessment = (fr.get("assessment_discussion") or "").strip()
    rec = (fr.get("recommendations") or "").strip()
    rx_draft = (fr.get("prescription_draft") or "").strip()

    visit_header = ""
    aid = getattr(session, "appointment_id", None)
    if aid:
        appt = await db.get(Appointment, aid)
        if appt:
            prac = await db.get(Practitioner, appt.practitioner_id)
            pname = prac.full_name if prac else "Your clinician"
            cc = (appt.chief_complaint or "").strip()
            visit_header = f"Booked visit context: {pname}."
            if cc:
                visit_header += f"\nReason on file: {cc}\n"
            else:
                visit_header += "\n"

    diagnosis = (summary[:500] if summary else "AI voice consultation").strip() or "AI voice consultation"
    parts: list[str] = []
    if summary:
        parts.append(f"Summary:\n{summary}")
    if assessment:
        parts.append(f"Discussion:\n{assessment}")
    if rec:
        parts.append(f"Recommendations:\n{rec}")
    if rx_draft:
        parts.append(f"Draft for discussion with your clinician:\n{rx_draft}")
    body_notes = "\n\n".join(parts) if parts else "AI voice consult completed. Please review with a licensed clinician."
    notes = f"{visit_header}\n{body_notes}".strip() if visit_header else body_notes

    prescription = Prescription(
        id=str(uuid.uuid4()),
        encounter_id=None,
        practitioner_id=None,
        patient_id=patient.id,
        voice_consult_session_id=session.id,
        status="ai_consult_record",
        diagnosis=diagnosis,
        notes=notes,
        is_signed=False,
    )
    db.add(prescription)
    await db.flush()

    instruct = rx_draft if rx_draft else notes[:8000]
    med = MedicationRequest(
        id=str(uuid.uuid4()),
        prescription_id=prescription.id,
        drug_id=None,
        drug_name="AI voice consult (not a formal prescription)",
        strength=None,
        dosage_form=None,
        route="oral",
        frequency="Discuss with your clinician",
        duration=None,
        quantity=None,
        instructions=instruct[:8000] if instruct else None,
    )
    db.add(med)

    await log_event(
        db,
        "voice_consult_prescription_saved",
        user_id=patient.user_id,
        resource_type="prescription",
        resource_id=prescription.id,
        metadata={"voice_consult_session_id": session.id},
    )
