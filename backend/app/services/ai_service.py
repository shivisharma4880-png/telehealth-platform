"""AI service: OpenAI Whisper transcription + GPT-4o SOAP note generation."""
from __future__ import annotations
import base64
import logging
import json
import tempfile
import os
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

AI_DOCTOR_SYSTEM_PROMPT = """You are "Dr. Assistant", a calm, professional-sounding voice companion while the patient is in a scheduled telehealth visit. They may also be speaking with a human clinician in the same session.

Rules:
- You are NOT a licensed physician. Do not claim to be their treating doctor. Do not diagnose, prescribe, or give medication dosing.
- Keep replies concise and natural for text-to-speech (roughly 3–8 short sentences unless they ask for a simpler explanation).
- Offer general education, clarify common terms, suggest questions they could ask their human clinician, and emotional reassurance when appropriate.
- If they describe possible emergencies (e.g. chest pain, stroke symptoms, severe bleeding, suicidal intent, inability to breathe), tell them to hang up and call local emergency services immediately; do not chat further about treatment.
- Never contradict urgent advice from emergency services or their human clinician."""


AUDIO_CALL_DOCTOR_PROMPT = """You are "Dr. Arjun", an AI placeholder doctor on a voice-only demo telehealth line. The patient is talking to you over a phone-style audio session (no video).

Speak in natural, conversational English as if on a call: warm, clear, usually 2–5 short sentences. Avoid bullet lists unless they ask for steps.

Rules:
- You are NOT a licensed physician; this is a product demo. If they ask, say clearly you are an AI assistant standing in for a doctor during development.
- Do not prescribe specific medications or doses. You may mention over-the-counter categories in general terms and urge a human clinician or pharmacist for anything specific.
- Do not give firm medical diagnoses; you may discuss common possibilities, red flags, and when to seek in-person care.
- Emergencies (chest pain, stroke symptoms, severe bleeding, suicidal intent, severe trouble breathing): tell them to end this demo and call local emergency services now.
- Keep answers concise so they work well when read aloud by the app."""


SOAP_SYSTEM_PROMPT = """You are a clinical documentation assistant helping a doctor generate SOAP notes from a teleconsultation transcript.

Generate a structured SOAP note from the provided consultation transcript. Return ONLY valid JSON with this exact structure:
{
  "subjective": "Patient's reported symptoms, history, and chief complaint in paragraph form",
  "objective": "Observed findings, reported vitals, physical examination findings mentioned in the transcript",
  "assessment": "Clinical assessment or diagnosis mentioned by the clinician (if stated)",
  "plan": "Treatment plan, medications discussed, investigations ordered, follow-up instructions",
  "diagnosis_codes": [],
  "investigations": "Any investigations or tests mentioned",
  "follow_up_notes": "Follow-up timing and instructions"
}

IMPORTANT:
- This is a DRAFT for clinician review and editing, not a final medical document
- Only include information explicitly stated in the transcript
- Use professional medical language
- If information is missing for a section, write "Not discussed in this consultation"
- Keep each section concise but complete"""


class AIService:
    """OpenAI-backed helpers; set OPENAI_API_KEY (repo root or backend `.env`)."""

    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None
        self._client_key: str | None = None

    @property
    def client(self) -> AsyncOpenAI | None:
        key = (settings.openai_api_key or "").strip()
        if not key:
            self._client = None
            self._client_key = None
            return None
        if self._client is None or self._client_key != key:
            self._client_key = key
            self._client = AsyncOpenAI(api_key=key)
        return self._client

    async def transcribe_audio_chunk(self, audio_data: bytes, language: str = "en") -> dict:
        """Transcribe audio using OpenAI Whisper."""
        if not self.client:
            logger.warning("OpenAI API key not configured; returning mock transcript")
            return {
                "text": "[Mock transcript] Patient reports fever and body ache for 2 days.",
                "confidence": 0.95,
                "language": "en",
            }

        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        try:
            with open(tmp_path, "rb") as audio_file:
                response = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language if language != "en" else None,
                    response_format="verbose_json",
                )
            return {
                "text": response.text,
                "confidence": 0.9,
                "language": response.language if hasattr(response, "language") else language,
            }
        finally:
            os.unlink(tmp_path)

    async def generate_soap_note(self, transcript: str, patient_context: dict | None = None) -> dict:
        """Generate a SOAP note draft from the consultation transcript using GPT-4o."""
        if not self.client:
            logger.warning("OpenAI API key not configured; returning mock SOAP note")
            return self._mock_soap_note()

        context_str = ""
        if patient_context:
            context_str = f"\n\nPatient Context: {json.dumps(patient_context)}"

        try:
            response = await self.client.chat.completions.create(
                model=settings.openai_soap_model,
                messages=[
                    {"role": "system", "content": SOAP_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"Consultation Transcript:{context_str}\n\n{transcript}\n\nGenerate the SOAP note JSON:",
                    },
                ],
                temperature=0.3,
                max_tokens=1500,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.error(f"GPT-4o SOAP generation failed: {e}")
            return self._mock_soap_note()

    async def ai_doctor_reply(
        self,
        user_message: str,
        history: list[dict],
        *,
        patient_first_name: str | None = None,
    ) -> str:
        """Conversational 'AI doctor assistant' for the patient consult UI (voice readout on client)."""
        name_bit = f" The patient's first name is {patient_first_name}." if patient_first_name else ""
        if not self.client:
            logger.warning("OpenAI API key not configured; returning mock AI doctor reply")
            return (
                "I'm a demo assistant — set OPENAI_API_KEY in your project root `.env` (or pass it into the API "
                "container) for full replies. I'm not a real doctor. Your human clinician in this visit is "
                "responsible for your care. How can I help you understand your visit or think of questions to ask them?"
            )

        messages: list[dict] = [
            {"role": "system", "content": AI_DOCTOR_SYSTEM_PROMPT + name_bit},
        ]
        for turn in history[-12:]:
            role = turn.get("role", "user")
            content = (turn.get("content") or "").strip()
            if role not in ("user", "assistant") or not content:
                continue
            messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_message.strip()})

        try:
            response = await self.client.chat.completions.create(
                model=settings.openai_chat_model,
                messages=messages,
                temperature=0.5,
                max_tokens=500,
            )
            text = (response.choices[0].message.content or "").strip()
            return text or "I'm here with you. Could you say that again in a few words?"
        except Exception as e:
            logger.error(f"AI doctor chat failed: {e}")
            return (
                "I'm having trouble reaching my language model right now. "
                "Please continue with your clinician in the video — they'll help you with medical decisions."
            )

    async def audio_call_doctor_reply(
        self,
        user_message: str,
        history: list[dict],
        *,
        patient_first_name: str | None = None,
    ) -> str:
        """Voice-only demo line: AI doctor responds to transcribed patient speech."""
        name_bit = f" Patient's first name: {patient_first_name}." if patient_first_name else ""
        if not self.client:
            logger.warning("OpenAI API key not configured; mock audio-call doctor reply")
            return (
                "Thanks for calling — I'm Dr. Arjun, an AI demo doctor on this line, not a licensed physician. "
                "Add an OpenAI API key to the server for full conversations. "
                "For now, tell me in a few words how you're feeling, and imagine I'm here to listen and suggest when a real doctor might help."
            )

        messages: list[dict] = [
            {"role": "system", "content": AUDIO_CALL_DOCTOR_PROMPT + name_bit},
        ]
        for turn in history[-16:]:
            role = turn.get("role", "user")
            content = (turn.get("content") or "").strip()
            if role not in ("user", "assistant") or not content:
                continue
            messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_message.strip()})

        try:
            response = await self.client.chat.completions.create(
                model=settings.openai_chat_model,
                messages=messages,
                temperature=0.55,
                max_tokens=400,
            )
            text = (response.choices[0].message.content or "").strip()
            return text or "I didn't quite catch that — could you say it again?"
        except Exception as e:
            logger.error(f"Audio-call doctor reply failed: {e}")
            return (
                "I'm having a brief technical issue. Please try speaking again in a moment, "
                "or call back your human clinic if you need urgent care."
            )

    def _mock_soap_note(self) -> dict:
        return {
            "subjective": "Patient reports fever of 38.5°C and body aches for the past 2 days. Also complains of mild sore throat and runny nose. No significant past medical history. No known drug allergies.",
            "objective": "Vitals not formally recorded during this teleconsultation. Patient appears alert and oriented. No acute respiratory distress reported.",
            "assessment": "Acute viral upper respiratory tract infection (URTI). Likely influenza-like illness.",
            "plan": "1. Paracetamol 500mg TDS for fever and pain relief\n2. Rest and adequate hydration\n3. Steam inhalation for nasal congestion\n4. Return if symptoms worsen or fever persists beyond 5 days\n5. Isolate as precaution",
            "diagnosis_codes": [],
            "investigations": "Not discussed in this consultation",
            "follow_up_notes": "Follow up in 5 days if not improving, or immediately if high fever (>39°C) or difficulty breathing.",
        }


ai_service = AIService()
