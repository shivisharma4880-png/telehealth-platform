from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

# Load monorepo `.env` even when uvicorn cwd is `backend/` (pydantic default is cwd-only).
_CORE_DIR = Path(__file__).resolve().parent
_BACKEND_ROOT = _CORE_DIR.parents[1]
_REPO_ROOT = _CORE_DIR.parents[2]


_env_file_candidates = (_REPO_ROOT / ".env", _BACKEND_ROOT / ".env")
_env_files = tuple(str(p) for p in _env_file_candidates if p.is_file())


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_files if _env_files else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "Telehealth Platform API"
    environment: str = "development"
    debug: bool = True

    # Database
    database_url: str = "postgresql://telehealth:telehealth_secret@localhost:5433/telehealth_db"

    # Auth
    jwt_secret: str = "supersecretjwtkey_change_in_production"
    jwt_refresh_secret: str = "supersecretrefreshjwtkey_change_in_production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # OpenAI (Dr. Assistant, SOAP drafts; not used for voice TTS)
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"  # consult sidebar + audio-call doctor
    openai_soap_model: str = "gpt-4o"

    # Groq (voice consult: STT + LLM + TTS on same API key)
    groq_api_key: str = ""
    groq_llm_model: str = "llama-3.3-70b-versatile"
    groq_stt_model: str = "whisper-large-v3-turbo"
    # TTS via Groq /audio/speech — playai-tts was decommissioned Dec 2025; use Orpheus (accept model terms in Groq Console).
    groq_tts_model: str = "canopylabs/orpheus-v1-english"
    groq_tts_voice: str = "troy"
    groq_tts_response_format: str = "wav"
    # Orpheus: max 200 chars/request (chunked in code). Unused excess if using another model later.
    groq_tts_max_input_chars: int = 200

    # Payment (mocked)
    razorpay_key_id: str = "mock"
    razorpay_key_secret: str = "mock"

    # SMS/Notifications (mocked)
    sms_provider_key: str = "mock"
    whatsapp_provider_key: str = "mock"

    # Storage
    pdf_storage_path: str = "./pdfs"

    # CORS
    allowed_origins: str = "http://localhost:3000"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


settings = Settings()
