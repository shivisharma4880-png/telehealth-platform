from pydantic import BaseModel, field_validator
from typing import Any


class AudioConsultTurnMessage(BaseModel):
    """Legacy shape for chat-style history validation."""

    role: str
    content: str

    @field_validator("role")
    @classmethod
    def role_ok(cls, v: str) -> str:
        if v not in ("user", "assistant"):
            raise ValueError('role must be "user" or "assistant"')
        return v


class VoiceConsultSessionCreateOut(BaseModel):
    session_id: str
    welcome_text: str
    welcome_audio_base64: str
    mime_type: str


class VoiceConsultTurnOut(BaseModel):
    transcript: str
    reply_text: str
    reply_audio_base64: str
    mime_type: str
    turn: int
    session_complete: bool
    final_result: dict[str, Any] | None = None
    summary_pdf_token: str | None = None


class LegacyAudioConsultTurnOut(BaseModel):
    """Pre–session-based API: text-only reply for older clients."""

    transcript: str
    reply: str
