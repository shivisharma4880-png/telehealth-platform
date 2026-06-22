"""Voice consult: Groq STT, LLM, and TTS (one API key); session storage and multi-turn flow."""

from __future__ import annotations

import base64
import json
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_patient
from app.models.user import User
from app.models.patient import Patient
from app.models.appointment import Appointment, AppointmentStatus
from app.models.voice_consult_session import VoiceConsultSession, VoiceConsultSessionStatus
from app.schemas.audio_consult import (
    AudioConsultTurnMessage,
    LegacyAudioConsultTurnOut,
    VoiceConsultSessionCreateOut,
    VoiceConsultTurnOut,
)
from app.services.groq_voice_service import GroqModelTermsRequired, VOICE_WELCOME_TEXT, groq_voice_service
from app.services.voice_consult_prescription import ensure_prescription_for_voice_session
from app.services.ai_visit_pdf_service import attach_ai_visit_summary_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audio-consult", tags=["Audio consult (Groq)"])

MAX_AUDIO_BYTES = 4 * 1024 * 1024
MAX_TURNS = 3


def _require_voice_consult_stack() -> None:
    if not groq_voice_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Voice consult is not configured. Set GROQ_API_KEY (STT, LLM, and TTS on Groq).",
        )


def _parse_client_history(raw: str) -> list[dict]:
    if not raw or not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    out: list[dict] = []
    for item in data[-20:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            out.append({"role": role, "content": content})
    return out


def _llm_history(messages: list) -> list[dict]:
    """Strip DB-only keys for the Groq service."""
    out: list[dict] = []
    for m in messages:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if role not in ("user", "assistant") or not content:
            continue
        out.append({"role": role, "content": content})
    return out


@router.post(
    "/turn",
    response_model=LegacyAudioConsultTurnOut,
    summary="[Legacy] Single turn without session (STT + LLM text reply)",
    description=(
        "Stateless voice turn: sends `messages_json` history from the client. "
        "Prefer POST /audio-consult/sessions for DB-backed sessions with OpenAI TTS."
    ),
)
async def audio_consult_turn_legacy(
    audio: UploadFile = File(..., description="Short recording, e.g. audio/webm from MediaRecorder"),
    messages_json: str = Form("[]"),
    current_user: User = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    """Backward-compatible endpoint for older frontends that still POST here."""
    if not groq_voice_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Voice consult is not configured. Set GROQ_API_KEY on the server.",
        )

    audio_bytes = await audio.read()
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio clip too large (max 4MB)")
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio")

    fname = audio.filename or "turn.webm"
    try:
        transcript_result = await groq_voice_service.transcribe_audio(audio_bytes, filename=fname)
    except Exception as e:
        logger.exception("Groq STT failed (legacy turn): %s", e)
        raise HTTPException(status_code=502, detail="Transcription failed. Try again.") from e

    transcript = (transcript_result.get("text") or "").strip()
    if not transcript:
        return LegacyAudioConsultTurnOut(
            transcript="",
            reply="I didn't catch that — try holding the button a little longer and speak clearly.",
        )

    history_raw = _parse_client_history(messages_json)
    clean_history: list[dict] = []
    for h in history_raw:
        try:
            m = AudioConsultTurnMessage(role=h["role"], content=h["content"])
            clean_history.append({"role": m.role, "content": m.content})
        except Exception:
            continue

    pat_res = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
    patient = pat_res.scalar_one_or_none()
    first = patient.first_name if patient else None

    try:
        reply = await groq_voice_service.followup_reply(
            transcript,
            clean_history,
            patient_first_name=first or None,
        )
    except Exception as e:
        logger.exception("Groq LLM failed (legacy turn): %s", e)
        raise HTTPException(status_code=502, detail="Assistant reply failed. Try again.") from e

    logger.info("audio_consult legacy turn: user=%s transcript_len=%s", current_user.id, len(transcript))
    return LegacyAudioConsultTurnOut(transcript=transcript, reply=reply)


@router.post("/sessions", response_model=VoiceConsultSessionCreateOut, summary="Start voice session with welcome TTS")
async def create_voice_consult_session(
    appointment_id: str | None = Query(
        None,
        description="Optional booked appointment this AI visit is for (patient must own it).",
    ),
    current_user: User = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    _require_voice_consult_stack()

    pat_res = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
    patient = pat_res.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=400, detail="Patient profile required.")

    linked_appointment_id: str | None = None
    if appointment_id:
        appt_res = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
        appt = appt_res.scalar_one_or_none()
        if not appt or appt.patient_id != patient.id:
            raise HTTPException(status_code=400, detail="Invalid appointment for this patient.")
        if appt.status not in (
            AppointmentStatus.BOOKED,
            AppointmentStatus.CONFIRMED,
            AppointmentStatus.IN_PROGRESS,
        ):
            raise HTTPException(
                status_code=400,
                detail="This appointment is not open for an AI visit. Book a new slot or contact the clinic.",
            )
        linked_appointment_id = appt.id

    welcome_text = VOICE_WELCOME_TEXT
    try:
        audio_bytes, mime = await groq_voice_service.text_to_speech(welcome_text)
    except GroqModelTermsRequired as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.exception("Welcome TTS failed: %s", e)
        raise HTTPException(status_code=502, detail="Could not generate welcome audio. Try again later.") from e

    b64 = base64.standard_b64encode(audio_bytes).decode("ascii")

    session = VoiceConsultSession(
        patient_id=patient.id,
        appointment_id=linked_appointment_id,
        status=VoiceConsultSessionStatus.IN_PROGRESS,
        messages=[{"role": "assistant", "content": welcome_text, "kind": "welcome"}],
        patient_turns_completed=0,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    logger.info("voice_consult session created user=%s session=%s", current_user.id, session.id)

    return VoiceConsultSessionCreateOut(
        session_id=session.id,
        welcome_text=welcome_text,
        welcome_audio_base64=b64,
        mime_type=mime,
    )


@router.post(
    "/sessions/{session_id}/turn",
    response_model=VoiceConsultTurnOut,
    summary="Patient audio turn: STT → LLM → TTS (3 rounds then final JSON)",
)
async def voice_consult_turn(
    session_id: str,
    audio: UploadFile = File(..., description="Short recording, e.g. audio/webm from MediaRecorder"),
    current_user: User = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    _require_voice_consult_stack()

    pat_res = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
    patient = pat_res.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=400, detail="Patient profile required.")

    sess_res = await db.execute(
        select(VoiceConsultSession).where(
            VoiceConsultSession.id == session_id,
            VoiceConsultSession.patient_id == patient.id,
        )
    )
    session = sess_res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    if session.status == VoiceConsultSessionStatus.COMPLETED or session.patient_turns_completed >= MAX_TURNS:
        raise HTTPException(status_code=400, detail="This session is already complete.")

    audio_bytes = await audio.read()
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio clip too large (max 4MB)")
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio")

    fname = audio.filename or "turn.webm"
    try:
        transcript_result = await groq_voice_service.transcribe_audio(audio_bytes, filename=fname)
    except Exception as e:
        logger.exception("Groq STT failed: %s", e)
        raise HTTPException(status_code=502, detail="Transcription failed. Try again.") from e

    transcript = (transcript_result.get("text") or "").strip()
    if not transcript:
        raise HTTPException(
            status_code=400,
            detail="Could not detect speech. Hold the button longer and speak clearly.",
        )

    turn_number = session.patient_turns_completed + 1
    history = _llm_history(session.messages)

    first_name = patient.first_name or None

    final_result = None
    reply_text = ""

    try:
        if turn_number < MAX_TURNS:
            reply_text = await groq_voice_service.followup_reply(
                transcript,
                history,
                patient_first_name=first_name,
            )
        else:
            spoken, final_result = await groq_voice_service.final_verdict(
                transcript,
                history,
                patient_first_name=first_name,
            )
            reply_text = spoken
    except Exception as e:
        logger.exception("Groq LLM failed: %s", e)
        raise HTTPException(status_code=502, detail="Assistant reply failed. Try again.") from e

    try:
        reply_audio, reply_mime = await groq_voice_service.text_to_speech(reply_text)
    except GroqModelTermsRequired as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.exception("Reply TTS failed: %s", e)
        raise HTTPException(status_code=502, detail="Could not synthesize voice reply. Try again.") from e

    msgs = list(session.messages or [])
    msgs.append({"role": "user", "content": transcript, "turn": turn_number})
    msgs.append({"role": "assistant", "content": reply_text, "turn": turn_number})
    if turn_number == MAX_TURNS:
        msgs[-1]["kind"] = "final"

    session.messages = msgs
    session.patient_turns_completed = turn_number
    summary_pdf_token: str | None = None
    if turn_number >= MAX_TURNS:
        session.status = VoiceConsultSessionStatus.COMPLETED
        session.final_result = final_result or {}
        await ensure_prescription_for_voice_session(db, session=session, patient=patient)
        try:
            summary_pdf_token = await attach_ai_visit_summary_pdf(db, session=session, patient=patient)
        except Exception as e:
            logger.exception("AI visit PDF attachment failed: %s", e)
            summary_pdf_token = None

    await db.commit()
    await db.refresh(session)

    reply_b64 = base64.standard_b64encode(reply_audio).decode("ascii")

    logger.info(
        "voice_consult turn user=%s session=%s turn=%s complete=%s",
        current_user.id,
        session.id,
        turn_number,
        session.status == VoiceConsultSessionStatus.COMPLETED,
    )

    return VoiceConsultTurnOut(
        transcript=transcript,
        reply_text=reply_text,
        reply_audio_base64=reply_b64,
        mime_type=reply_mime,
        turn=turn_number,
        session_complete=session.status == VoiceConsultSessionStatus.COMPLETED,
        final_result=final_result if turn_number == MAX_TURNS else None,
        summary_pdf_token=summary_pdf_token if turn_number == MAX_TURNS else None,
    )
