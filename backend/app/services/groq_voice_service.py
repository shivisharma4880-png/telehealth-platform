"""Groq STT, LLM, and TTS (same GROQ_API_KEY) for the voice consult demo."""

from __future__ import annotations

import io
import json
import logging
import re
import wave
from typing import Any

import httpx
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

GROQ_OPENAI_BASE = "https://api.groq.com/openai/v1"


class GroqModelTermsRequired(RuntimeError):
    """Groq TTS returned model_terms_required — org admin must accept model terms in Groq Console."""


def _tts_chunk_limit() -> int:
    """Orpheus allows 200 chars/request; playai-tts supports much longer inputs."""
    m = (settings.groq_tts_model or "").lower()
    cap = max(1, settings.groq_tts_max_input_chars)
    if "orpheus" in m:
        return min(200, cap)
    return min(cap, 10000)


def _split_tts_text(text: str, max_len: int) -> list[str]:
    """Split text so each segment stays within the TTS provider per-request limit."""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= max_len:
        return [text]
    chunks: list[str] = []
    rest = text
    seps = (". ", "! ", "? ", ".\n", "!\n", "?\n", "\n")
    while rest:
        if len(rest) <= max_len:
            chunks.append(rest)
            break
        chunk_region = rest[:max_len]
        cut = -1
        for sep in seps:
            idx = chunk_region.rfind(sep)
            if idx >= max_len // 3:
                cut = idx + len(sep)
                break
        if cut > 0:
            chunks.append(rest[:cut].strip())
            rest = rest[cut:].lstrip()
            continue
        sp = chunk_region.rfind(" ")
        if sp >= max_len // 4:
            chunks.append(rest[:sp].strip())
            rest = rest[sp:].lstrip()
        else:
            chunks.append(rest[:max_len].strip())
            rest = rest[max_len:].lstrip()
    return [c for c in chunks if c]


def _concat_wav_bytes(parts: list[bytes]) -> bytes:
    """Merge multiple WAV files with identical sample format (channels/rate/width)."""
    if not parts:
        return b""
    if len(parts) == 1:
        return parts[0]

    frames = b""
    with wave.open(io.BytesIO(parts[0]), "rb") as w0:
        p0 = w0.getparams()
        frames = w0.readframes(w0.getnframes())

    nchannels, sampwidth, framerate, _, comptype, compname = p0
    bytes_per_frame = nchannels * sampwidth
    if bytes_per_frame <= 0:
        raise ValueError("Invalid WAV parameters from TTS")

    for p in parts[1:]:
        with wave.open(io.BytesIO(p), "rb") as wi:
            pi = wi.getparams()
            if (
                pi.nchannels,
                pi.sampwidth,
                pi.framerate,
                pi.comptype,
                pi.compname,
            ) != (nchannels, sampwidth, framerate, comptype, compname):
                raise ValueError("TTS returned mismatched WAV parameters between chunks")
            frames += wi.readframes(wi.getnframes())

    total_nframes = len(frames) // bytes_per_frame
    if total_nframes * bytes_per_frame != len(frames):
        raise ValueError("WAV PCM length is not aligned to frame size")

    merged_params = (nchannels, sampwidth, framerate, total_nframes, comptype, compname)
    out = io.BytesIO()
    with wave.open(out, "wb") as wo:
        wo.setparams(merged_params)
        wo.writeframes(frames)
    return out.getvalue()


VOICE_WELCOME_TEXT = (
    "Hey — thanks for jumping on. I'm Dr. Arjun, an AI assistant on this demo line, not a real doctor. "
    "We'll keep it to three short voice turns: I'll ask a couple of follow-ups so I understand you better, "
    "then I'll wrap up with a plain-language recap you can take to a clinician. "
    "If something I ask doesn't make sense, or you misspoke, just say so and we'll sort it out. "
    "Whenever you're ready, hold the mic and tell me in your own words what's going on today."
)

FOLLOWUP_SYSTEM = """You are "Dr. Arjun", a calm, personable AI assistant on a voice-only demo telehealth line (not a licensed physician, not replacing a doctor).

The patient is speaking in short voice clips. Your reply will be read aloud by text-to-speech — write the way a thoughtful clinician might *talk*: natural contractions, short sentences, one idea at a time. No bullet lists, no markdown, no emojis, no stage directions in brackets. Never repeat or quote any bracketed "session notes" if they appear in the user message — those are only for you.

Your job this turn:
1) Briefly react to what they actually said (one short phrase — vary your wording; do **not** open every turn with the same filler like "Thank you for sharing" or "I appreciate that").
2) If their answer is **vague, off-topic, joking, nonsensical, or doesn't answer what you last asked**, do **not** give generic medical reassurance or a canned lecture. Instead, gently say you didn't quite catch it (or that it doesn't match what you asked) and ask **one** specific, concrete follow-up — e.g. when it started, how bad on a simple scale, what makes it better or worse, or one clarifying yes/no.
3) If they **did** answer clearly enough to move forward, ask **one** focused next question about symptoms, timing, severity, or context.

Rules:
- Never invent symptoms or history they didn't mention.
- Do not diagnose or prescribe specific medications or doses.
- Do not claim to be a licensed physician.
- Emergencies (chest pain, stroke symptoms, severe bleeding, suicidal intent, severe breathing trouble): tell them to seek emergency care now, briefly, then stop probing.

Length: about 2–5 short sentences total."""

FINAL_SYSTEM = """You are "Dr. Arjun", closing a three-turn demo voice consultation as an AI assistant (not a licensed physician).

Based on the **actual** conversation, respond with ONLY valid JSON (no markdown fences) using exactly these keys:
{
  "spoken_closure": "string — 3–6 sentences read aloud by TTS; sound human and direct, like wrapping up a phone call. If the patient never gave clear specifics, say so honestly — do not fabricate a detailed story. Still encourage them to see a licensed clinician with the details they *do* have. Remind them this was educational only.",
  "summary": "string — brief recap of what they actually said; if sparse, say what was unclear instead of guessing",
  "assessment_discussion": "string — general possibilities only in cautious language, or state that there wasn't enough detail to discuss causes",
  "recommendations": "string — practical next steps (rest, hydration, when to seek care) only if grounded in what they said; otherwise focus on what to tell a clinician or pharmacist",
  "prescription_draft": "string — explicitly labeled as a non-prescription draft for discussion with a clinician; no specific drug names with doses unless clearly OTC general categories; urge human prescribing for anything prescription-only"
}

Safety:
- Do not output specific prescription dosing (mg, frequency) for prescription medications.
- Frame everything as guidance to confirm with a qualified clinician."""


def _followup_clarification_hint(user_message: str) -> str:
    """Nudge the model when the transcript is likely too thin to respond substantively."""
    u = (user_message or "").strip()
    if not u:
        return "\n\n[Session note: The patient’s clip had no usable text — ask them to repeat a bit louder, one symptom or worry at a time.]"
    low = u.lower()
    vague_phrases = {
        "i don't know",
        "dont know",
        "don't know",
        "idk",
        "not sure",
        "maybe",
        "nothing",
        "no idea",
        "dunno",
        "same",
        "whatever",
        "i guess",
        "not really",
        "huh",
        "what",
    }
    if len(u) < 18 or low in vague_phrases or any(low == p or low.startswith(p + " ") for p in vague_phrases):
        return (
            "\n\n[Session note: Their answer is very short or non-specific. "
            "Do not fill in with generic medical advice — ask one clear, concrete follow-up, or invite them to restate.]"
        )
    return ""


PDF_DOCUMENT_SYSTEM = """You format an AI demo telehealth voice consultation for a patient-facing PDF document.

You will receive the full conversation as plain text, and optionally a JSON hint from an earlier model pass.

Respond with ONLY valid JSON (no markdown fences) using exactly these keys:
{
  "visit_summary": "string — 2–4 short paragraphs of plain text summarizing what was discussed",
  "prescription_section": "string — draft guidance for the patient; NOT a legal prescription; plain text; urge confirming with a licensed clinician or pharmacist",
  "safety_disclaimer": "string — one short paragraph stating this is a demo, not a licensed physician, educational only"
}

Rules:
- Plain text only inside JSON values (no HTML tags, no markdown).
- Stay consistent with the conversation; do not invent medications or doses.
- Do not output specific prescription dosing (mg, frequency) for prescription-only drugs."""


class GroqVoiceService:
    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None
        if settings.groq_api_key:
            self._client = AsyncOpenAI(api_key=settings.groq_api_key, base_url=GROQ_OPENAI_BASE)

    def is_configured(self) -> bool:
        return self._client is not None

    def is_tts_configured(self) -> bool:
        """TTS uses the same Groq API key as STT/LLM."""
        return self._client is not None

    def _require_client(self) -> AsyncOpenAI:
        if not self._client:
            raise RuntimeError("GROQ_API_KEY is not configured")
        return self._client

    async def transcribe_audio(self, audio_data: bytes, filename: str = "recording.webm") -> dict[str, Any]:
        """Transcribe audio via Groq Whisper-compatible API."""
        client = self._require_client()
        bio = io.BytesIO(audio_data)
        bio.name = filename
        response = await client.audio.transcriptions.create(
            file=bio,
            model=settings.groq_stt_model,
            language="en",
            response_format="json",
            temperature=0.0,
        )
        text = (getattr(response, "text", None) or "").strip()
        return {"text": text, "language": getattr(response, "language", None) or "en"}

    async def text_to_speech(self, text: str) -> tuple[bytes, str]:
        """Synthesize speech via Groq /audio/speech (Orpheus, etc.). Long text is chunked and WAV-stitched."""
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is not configured")
        max_len = _tts_chunk_limit()
        chunks = _split_tts_text(text, max_len)
        if not chunks:
            raise ValueError("Empty text for TTS")
        fmt = settings.groq_tts_response_format.lower()
        mime = "audio/wav" if fmt == "wav" else "audio/mpeg"

        async with httpx.AsyncClient() as http:
            audio_parts: list[bytes] = []
            for ch in chunks:
                r = await http.post(
                    f"{GROQ_OPENAI_BASE}/audio/speech",
                    headers={
                        "Authorization": f"Bearer {settings.groq_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.groq_tts_model,
                        "voice": settings.groq_tts_voice,
                        "input": ch,
                        "response_format": settings.groq_tts_response_format,
                    },
                    timeout=120.0,
                )
                if r.status_code >= 400:
                    logger.error("Groq TTS HTTP %s: %s", r.status_code, (r.text or "")[:800])
                    try:
                        payload = r.json()
                        err = payload.get("error") or {}
                        if err.get("code") == "model_terms_required":
                            raise GroqModelTermsRequired(
                                err.get("message")
                                or "This TTS model requires terms acceptance in the Groq Console."
                            )
                    except GroqModelTermsRequired:
                        raise
                    except Exception:
                        pass
                    r.raise_for_status()
                audio_parts.append(r.content)

        if len(audio_parts) == 1:
            return audio_parts[0], mime
        if fmt != "wav":
            raise RuntimeError(
                "Long TTS text requires GROQ_TTS_RESPONSE_FORMAT=wav to combine chunks."
            )
        return _concat_wav_bytes(audio_parts), mime

    def _history_messages(self, history: list[dict[str, Any]]) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for turn in history[-16:]:
            role = turn.get("role")
            content = (turn.get("content") or "").strip()
            if role not in ("user", "assistant") or not content:
                continue
            out.append({"role": role, "content": content})
        return out

    async def followup_reply(
        self,
        user_message: str,
        history: list[dict[str, Any]],
        *,
        patient_first_name: str | None = None,
    ) -> str:
        client = self._require_client()
        name_bit = f" The patient's first name is {patient_first_name}." if patient_first_name else ""
        messages: list[dict[str, str]] = [{"role": "system", "content": FOLLOWUP_SYSTEM + name_bit}]
        messages.extend(self._history_messages(history))
        user_block = user_message.strip() + _followup_clarification_hint(user_message)
        messages.append({"role": "user", "content": user_block})

        response = await client.chat.completions.create(
            model=settings.groq_llm_model,
            messages=messages,
            temperature=0.78,
            max_tokens=420,
        )
        text = (response.choices[0].message.content or "").strip()
        return (
            text
            or "Sorry — I didn't quite catch that. In a few words, what's bothering you most today, and when did you first notice it?"
        )

    async def final_verdict(
        self,
        user_message: str,
        history: list[dict[str, Any]],
        *,
        patient_first_name: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Returns (spoken_closure for TTS, full structured dict for DB/UI)."""
        client = self._require_client()
        name_bit = f" The patient's first name is {patient_first_name}." if patient_first_name else ""
        messages: list[dict[str, str]] = [{"role": "system", "content": FINAL_SYSTEM + name_bit}]
        messages.extend(self._history_messages(history))
        messages.append({"role": "user", "content": user_message.strip()})

        raw_content = ""
        try:
            response = await client.chat.completions.create(
                model=settings.groq_llm_model,
                messages=messages,
                temperature=0.5,
                max_tokens=1200,
                response_format={"type": "json_object"},
            )
            raw_content = (response.choices[0].message.content or "").strip()
        except Exception as e:
            logger.warning("JSON response_format retry without json_object: %s", e)
            response = await client.chat.completions.create(
                model=settings.groq_llm_model,
                messages=messages,
                temperature=0.5,
                max_tokens=1200,
            )
            raw_content = (response.choices[0].message.content or "").strip()

        data = self._parse_final_json(raw_content)
        spoken = (data.get("spoken_closure") or "").strip()
        if not spoken:
            spoken = (
                "Alright — that's all we have time for on this demo line. "
                "Take whatever you could share to a licensed clinician who can actually examine you and sort out next steps. "
                "This wasn't a real visit, just a voice check-in."
            )
        return spoken, data

    def _parse_final_json(self, raw: str) -> dict[str, Any]:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
        return {
            "spoken_closure": raw[:1200] if raw else "",
            "summary": "",
            "assessment_discussion": "",
            "recommendations": "",
            "prescription_draft": "",
        }

    async def pdf_document_payload(
        self,
        conversation_text: str,
        final_result_hint: dict[str, Any] | None,
    ) -> dict[str, str]:
        """Second-pass LLM: structured fields for visit summary PDF."""
        client = self._require_client()
        hint = ""
        if final_result_hint:
            try:
                hint = "\n\nStructured hint (may omit details):\n" + json.dumps(final_result_hint, ensure_ascii=False)[
                    :6000
                ]
            except Exception:
                hint = ""
        user_content = (conversation_text or "").strip()[:12000] + hint
        if not user_content.strip():
            return {
                "visit_summary": "No transcript available.",
                "prescription_section": "No draft discussion recorded.",
                "safety_disclaimer": (
                    "This document is from an AI demo only. It is not medical advice. "
                    "See a licensed clinician for diagnosis and treatment."
                ),
            }

        messages: list[dict[str, str]] = [
            {"role": "system", "content": PDF_DOCUMENT_SYSTEM},
            {"role": "user", "content": user_content},
        ]
        try:
            response = await client.chat.completions.create(
                model=settings.groq_llm_model,
                messages=messages,
                temperature=0.25,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )
            raw = (response.choices[0].message.content or "").strip()
            data = json.loads(raw) if raw else {}
            if not isinstance(data, dict):
                raise ValueError("not a dict")
        except Exception as e:
            logger.warning("pdf_document_payload LLM failed: %s", e)
            return _fallback_pdf_fields(final_result_hint)

        vs = (data.get("visit_summary") or "").strip()
        ps = (data.get("prescription_section") or "").strip()
        sd = (data.get("safety_disclaimer") or "").strip()
        if not vs or not ps:
            fb = _fallback_pdf_fields(final_result_hint)
            return {
                "visit_summary": vs or fb["visit_summary"],
                "prescription_section": ps or fb["prescription_section"],
                "safety_disclaimer": sd or fb["safety_disclaimer"],
            }
        return {
            "visit_summary": vs,
            "prescription_section": ps,
            "safety_disclaimer": sd
            or (
                "This is an AI-assisted demo only. It is not a substitute for care from a licensed clinician. "
                "Confirm any medications or treatment with your doctor or pharmacist."
            ),
        }


def _fallback_pdf_fields(final_result: dict[str, Any] | None) -> dict[str, str]:
    fr = final_result or {}
    parts: list[str] = []
    for k in ("summary", "assessment_discussion", "recommendations"):
        v = (fr.get(k) or "").strip()
        if v:
            parts.append(v)
    visit_summary = "\n\n".join(parts) if parts else "No summary available."
    prescription_section = (fr.get("prescription_draft") or "").strip() or "No draft care discussion recorded."
    safety = (
        "This is an AI-assisted demo only. It is not a substitute for care from a licensed clinician. "
        "Confirm any medications or treatment with your doctor or pharmacist."
    )
    return {
        "visit_summary": visit_summary,
        "prescription_section": prescription_section,
        "safety_disclaimer": safety,
    }


groq_voice_service = GroqVoiceService()
