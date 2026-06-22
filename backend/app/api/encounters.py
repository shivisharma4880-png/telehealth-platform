from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
import asyncio
import json
import uuid

from app.core.database import get_db
from app.core.deps import get_current_user, get_current_clinician, get_current_patient
from app.models.user import User, UserRole
from app.models.encounter import Encounter, EncounterStatus, NoteStatus, TranscriptSegment
from app.models.appointment import Appointment, AppointmentStatus
from app.models.medication import Prescription, MedicationRequest
from app.services.prescription_signing import sign_prescription_entity
from app.models.practitioner import Practitioner
from app.models.patient import Patient
from app.schemas.encounter import (
    EncounterOut,
    SOAPNoteUpdate,
    SOAPNoteFinalize,
    TranscriptSegmentOut,
    AIDoctorChatIn,
    AIDoctorChatOut,
)
from app.services.ai_service import ai_service
from app.services.audit_service import log_event

router = APIRouter(prefix="/encounters", tags=["Encounters"])


@router.post(
    "/{encounter_id}/ai-doctor/message",
    response_model=AIDoctorChatOut,
    summary="Patient AI companion during a scheduled visit (educational only)",
)
async def ai_doctor_message(
    encounter_id: str,
    body: AIDoctorChatIn,
    current_user: User = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Encounter).where(Encounter.id == encounter_id))
    encounter = result.scalar_one_or_none()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")

    pat_res = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
    patient = pat_res.scalar_one_or_none()
    if not patient or patient.id != encounter.patient_id:
        raise HTTPException(status_code=403, detail="Not authorized for this encounter")

    hist = [{"role": m.role, "content": m.content} for m in body.history]
    reply = await ai_service.ai_doctor_reply(
        body.message,
        hist,
        patient_first_name=patient.first_name or None,
    )
    return AIDoctorChatOut(reply=reply)


@router.post("/{encounter_id}/start", summary="Start the consultation (clinician)")
async def start_consultation(
    encounter_id: str,
    current_user: User = Depends(get_current_clinician),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Encounter).where(Encounter.id == encounter_id))
    encounter = result.scalar_one_or_none()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")

    prac_res = await db.execute(select(Practitioner).where(Practitioner.user_id == current_user.id))
    practitioner = prac_res.scalar_one_or_none()
    if not practitioner or practitioner.id != encounter.practitioner_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    encounter.status = EncounterStatus.IN_PROGRESS
    encounter.call_started_at = datetime.now(timezone.utc)

    appt_res = await db.execute(select(Appointment).where(Appointment.id == encounter.appointment_id))
    appt = appt_res.scalar_one_or_none()
    if appt:
        appt.status = AppointmentStatus.IN_PROGRESS

    await log_event(db, "consultation_started", user_id=current_user.id, resource_type="encounter",
                    resource_id=encounter_id)
    await db.commit()

    return {"message": "Consultation started"}


@router.post("/{encounter_id}/end", summary="End the consultation (clinician)")
async def end_consultation(
    encounter_id: str,
    request: Request,
    current_user: User = Depends(get_current_clinician),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Encounter).where(Encounter.id == encounter_id))
    encounter = result.scalar_one_or_none()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")

    prac_res = await db.execute(select(Practitioner).where(Practitioner.user_id == current_user.id))
    practitioner = prac_res.scalar_one_or_none()
    if not practitioner or practitioner.id != encounter.practitioner_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    encounter.status = EncounterStatus.COMPLETED
    encounter.call_ended_at = datetime.now(timezone.utc)
    if encounter.call_started_at:
        delta = encounter.call_ended_at - encounter.call_started_at
        encounter.duration_minutes = int(delta.total_seconds() / 60)

    appt_res = await db.execute(select(Appointment).where(Appointment.id == encounter.appointment_id))
    appt = appt_res.scalar_one_or_none()
    if appt:
        appt.status = AppointmentStatus.COMPLETED

    # Build full transcript from segments
    seg_res = await db.execute(
        select(TranscriptSegment)
        .where(TranscriptSegment.encounter_id == encounter_id)
        .order_by(TranscriptSegment.created_at)
    )
    segments = seg_res.scalars().all()
    if segments:
        encounter.full_transcript = "\n".join([f"[{s.speaker}]: {s.text}" for s in segments])

    # Sign any draft prescriptions for this visit (patient sees them under My Records)
    draft_res = await db.execute(
        select(Prescription).where(
            Prescription.encounter_id == encounter_id,
            Prescription.is_signed.is_(False),
            Prescription.practitioner_id == practitioner.id,
            Prescription.practitioner_id.is_not(None),
        )
    )
    for rx in draft_res.scalars().all():
        await sign_prescription_entity(db, rx, signing_user_id=current_user.id, request=request)

    signed_any = await db.execute(
        select(Prescription.id).where(
            Prescription.encounter_id == encounter_id,
            Prescription.is_signed.is_(True),
        ).limit(1)
    )
    if signed_any.scalar_one_or_none() is None:
        soap_parts: list[str] = []
        for label, val in (
            ("Subjective", encounter.soap_subjective),
            ("Objective", encounter.soap_objective),
            ("Assessment", encounter.soap_assessment),
            ("Plan", encounter.soap_plan),
        ):
            if val and str(val).strip():
                soap_parts.append(f"{label}:\n{str(val).strip()}")
        trx = (encounter.full_transcript or "").strip()
        if trx:
            soap_parts.append(f"Visit transcript:\n{trx[:8000]}")
        if soap_parts:
            body_txt = "\n\n".join(soap_parts)
            diag_src = (
                encounter.soap_assessment
                or encounter.soap_plan
                or encounter.soap_subjective
                or "Consultation summary"
            )
            diag = str(diag_src).strip()[:500] or "Consultation summary"
            new_id = str(uuid.uuid4())
            rx = Prescription(
                id=new_id,
                encounter_id=encounter_id,
                practitioner_id=practitioner.id,
                patient_id=encounter.patient_id,
                status="draft",
                diagnosis=diag,
                notes=body_txt[:12000] if len(body_txt) > 12000 else body_txt,
            )
            db.add(rx)
            await db.flush()
            med = MedicationRequest(
                id=str(uuid.uuid4()),
                prescription_id=new_id,
                drug_name="See visit documentation below",
                drug_id=None,
                strength=None,
                dosage_form=None,
                route="oral",
                frequency="As directed by your clinician",
                duration=None,
                quantity=None,
                instructions="Confirm all medications and next steps with your prescribing clinician.",
            )
            db.add(med)
            await log_event(
                db,
                "prescription_created",
                user_id=current_user.id,
                resource_type="prescription",
                resource_id=new_id,
                description="Auto-generated when consultation ended",
                ip_address=request.client.host if request.client else None,
            )
            await sign_prescription_entity(db, rx, signing_user_id=current_user.id, request=request)

    await log_event(db, "consultation_ended", user_id=current_user.id, resource_type="encounter",
                    resource_id=encounter_id, metadata={"duration_minutes": encounter.duration_minutes})
    await db.commit()

    return {"message": "Consultation ended", "duration_minutes": encounter.duration_minutes}


@router.post("/{encounter_id}/transcribe", summary="Upload audio chunk for transcription")
async def transcribe_audio(
    encounter_id: str,
    audio_file: UploadFile = File(...),
    speaker: str = "clinician",
    current_user: User = Depends(get_current_clinician),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Encounter).where(Encounter.id == encounter_id))
    encounter = result.scalar_one_or_none()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")

    audio_data = await audio_file.read()
    transcript_result = await ai_service.transcribe_audio_chunk(audio_data)

    segment = TranscriptSegment(
        id=str(uuid.uuid4()),
        encounter_id=encounter_id,
        speaker=speaker,
        text=transcript_result["text"],
        confidence=transcript_result.get("confidence"),
    )
    db.add(segment)
    await db.commit()

    return {
        "segment_id": segment.id,
        "text": segment.text,
        "confidence": transcript_result.get("confidence"),
    }


@router.get("/{encounter_id}/transcript/stream", summary="SSE stream of transcript segments")
async def stream_transcript(
    encounter_id: str,
    current_user: User = Depends(get_current_clinician),
    db: AsyncSession = Depends(get_db),
):
    """Stream transcript segments via Server-Sent Events."""
    result = await db.execute(select(Encounter).where(Encounter.id == encounter_id))
    encounter = result.scalar_one_or_none()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")

    async def event_generator():
        from app.core.database import AsyncSessionLocal
        last_count = 0
        while True:
            async with AsyncSessionLocal() as session:
                seg_res = await session.execute(
                    select(TranscriptSegment)
                    .where(TranscriptSegment.encounter_id == encounter_id)
                    .order_by(TranscriptSegment.created_at)
                    .offset(last_count)
                )
                new_segments = seg_res.scalars().all()
                for seg in new_segments:
                    data = json.dumps({"id": seg.id, "speaker": seg.speaker, "text": seg.text})
                    yield f"data: {data}\n\n"
                    last_count += 1

                enc_check = await session.get(Encounter, encounter_id)
                if enc_check and enc_check.status == EncounterStatus.COMPLETED:
                    yield "data: {\"event\": \"end\"}\n\n"
                    break

            await asyncio.sleep(2)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/{encounter_id}/generate-notes", summary="Generate AI draft SOAP notes (GPT-4o)")
async def generate_soap_notes(
    encounter_id: str,
    current_user: User = Depends(get_current_clinician),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Encounter).where(Encounter.id == encounter_id))
    encounter = result.scalar_one_or_none()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")

    prac_res = await db.execute(select(Practitioner).where(Practitioner.user_id == current_user.id))
    practitioner = prac_res.scalar_one_or_none()
    if not practitioner or practitioner.id != encounter.practitioner_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if encounter.soap_generated_count >= 2:
        raise HTTPException(status_code=400, detail="Maximum SOAP note generation attempts reached (2 per consult)")

    # Get full transcript
    seg_res = await db.execute(
        select(TranscriptSegment)
        .where(TranscriptSegment.encounter_id == encounter_id)
        .order_by(TranscriptSegment.created_at)
    )
    segments = seg_res.scalars().all()

    transcript = encounter.full_transcript
    if not transcript and segments:
        transcript = "\n".join([f"[{s.speaker}]: {s.text}" for s in segments])
    if not transcript:
        transcript = "No transcript available yet."

    # Patient context
    pat_res = await db.execute(select(Patient).where(Patient.id == encounter.patient_id))
    patient = pat_res.scalar_one_or_none()
    patient_context = None
    if patient:
        patient_context = {
            "name": patient.full_name,
            "allergies": patient.allergies,
            "medical_history": patient.medical_history,
        }

    soap = await ai_service.generate_soap_note(transcript, patient_context)

    encounter.soap_subjective = soap.get("subjective", "")
    encounter.soap_objective = soap.get("objective", "")
    encounter.soap_assessment = soap.get("assessment", "")
    encounter.soap_plan = soap.get("plan", "")
    encounter.investigations = soap.get("investigations", "")
    encounter.follow_up_notes = soap.get("follow_up_notes", "")
    encounter.soap_generated_count += 1
    encounter.soap_note_status = NoteStatus.DRAFT

    await log_event(db, "soap_note_generated", user_id=current_user.id, resource_type="encounter",
                    resource_id=encounter_id, metadata={"attempt": encounter.soap_generated_count})
    await db.commit()
    await db.refresh(encounter)

    return {
        "status": "draft",
        "note": {
            "subjective": encounter.soap_subjective,
            "objective": encounter.soap_objective,
            "assessment": encounter.soap_assessment,
            "plan": encounter.soap_plan,
            "investigations": encounter.investigations,
            "follow_up_notes": encounter.follow_up_notes,
        },
        "generated_count": encounter.soap_generated_count,
        "warning": "AI-generated draft. Please review and edit before finalizing.",
    }


@router.patch("/{encounter_id}/notes", response_model=EncounterOut, summary="Update SOAP note draft")
async def update_soap_notes(
    encounter_id: str,
    body: SOAPNoteUpdate,
    request: Request,
    current_user: User = Depends(get_current_clinician),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Encounter).where(Encounter.id == encounter_id))
    encounter = result.scalar_one_or_none()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(encounter, field, value)

    await log_event(db, "soap_note_edited", user_id=current_user.id, resource_type="encounter",
                    resource_id=encounter_id, ip_address=request.client.host if request.client else None)
    await db.commit()
    await db.refresh(encounter)
    return encounter


@router.post("/{encounter_id}/notes/finalize", response_model=EncounterOut, summary="Finalize SOAP notes")
async def finalize_soap_notes(
    encounter_id: str,
    body: SOAPNoteFinalize,
    request: Request,
    current_user: User = Depends(get_current_clinician),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Encounter).where(Encounter.id == encounter_id))
    encounter = result.scalar_one_or_none()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")

    prac_res = await db.execute(select(Practitioner).where(Practitioner.user_id == current_user.id))
    practitioner = prac_res.scalar_one_or_none()
    if not practitioner or practitioner.id != encounter.practitioner_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(encounter, field, value)

    encounter.soap_note_status = NoteStatus.FINAL
    encounter.soap_finalized_at = datetime.now(timezone.utc)

    await log_event(db, "soap_note_finalized", user_id=current_user.id, resource_type="encounter",
                    resource_id=encounter_id, ip_address=request.client.host if request.client else None)
    await db.commit()
    await db.refresh(encounter)
    return encounter


@router.get("/{encounter_id}", response_model=EncounterOut)
async def get_encounter(
    encounter_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Encounter).where(Encounter.id == encounter_id))
    encounter = result.scalar_one_or_none()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")

    if current_user.role == UserRole.PATIENT:
        pat_res = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
        patient = pat_res.scalar_one_or_none()
        if not patient or patient.id != encounter.patient_id:
            raise HTTPException(status_code=403, detail="Not authorized for this encounter")
    elif current_user.role == UserRole.CLINICIAN:
        prac_res = await db.execute(select(Practitioner).where(Practitioner.user_id == current_user.id))
        practitioner = prac_res.scalar_one_or_none()
        if not practitioner or practitioner.id != encounter.practitioner_id:
            raise HTTPException(status_code=403, detail="Not authorized for this encounter")

    return encounter


@router.get("/{encounter_id}/transcript", response_model=list[TranscriptSegmentOut])
async def get_transcript(
    encounter_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TranscriptSegment)
        .where(TranscriptSegment.encounter_id == encounter_id)
        .order_by(TranscriptSegment.created_at)
    )
    return result.scalars().all()
