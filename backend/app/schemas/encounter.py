from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.encounter import EncounterStatus, NoteStatus


class TranscriptSegmentOut(BaseModel):
    id: str
    speaker: str
    text: str
    confidence: Optional[float] = None
    start_offset_seconds: Optional[float] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class SOAPNoteUpdate(BaseModel):
    soap_subjective: Optional[str] = None
    soap_objective: Optional[str] = None
    soap_assessment: Optional[str] = None
    soap_plan: Optional[str] = None
    diagnosis_codes: Optional[List[str]] = None
    investigations: Optional[str] = None
    follow_up_notes: Optional[str] = None
    vitals: Optional[Dict[str, Any]] = None


class SOAPNoteFinalize(SOAPNoteUpdate):
    pass


class EncounterOut(BaseModel):
    id: str
    appointment_id: str
    practitioner_id: str
    patient_id: str
    status: EncounterStatus
    call_started_at: Optional[datetime] = None
    call_ended_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    full_transcript: Optional[str] = None
    transcription_enabled: bool
    soap_note_status: NoteStatus
    soap_subjective: Optional[str] = None
    soap_objective: Optional[str] = None
    soap_assessment: Optional[str] = None
    soap_plan: Optional[str] = None
    soap_generated_count: int
    soap_finalized_at: Optional[datetime] = None
    diagnosis_codes: Optional[List[str]] = None
    investigations: Optional[str] = None
    follow_up_notes: Optional[str] = None
    vitals: Optional[Dict[str, Any]] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class TranscriptUpload(BaseModel):
    audio_chunk_base64: str
    speaker: str = "unknown"
    chunk_index: int = 0


class AIDoctorChatMessage(BaseModel):
    role: str
    content: str

    @field_validator("role")
    @classmethod
    def role_must_be_chat(cls, v: str) -> str:
        if v not in ("user", "assistant"):
            raise ValueError('role must be "user" or "assistant"')
        return v


class AIDoctorChatIn(BaseModel):
    message: str
    history: List[AIDoctorChatMessage] = []


class AIDoctorChatOut(BaseModel):
    reply: str
