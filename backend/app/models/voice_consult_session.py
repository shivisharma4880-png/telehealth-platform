from __future__ import annotations
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.appointment import Appointment
    from app.models.patient import Patient
    from app.models.medication import Prescription
from app.core.database import Base
from app.core.sa_enum import enum_values


class VoiceConsultSessionStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class VoiceConsultSession(Base):
    """Stores one AI voice demo consult: welcome + up to 3 patient turns and optional final JSON verdict."""

    __tablename__ = "voice_consult_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    appointment_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[VoiceConsultSessionStatus] = mapped_column(
        SAEnum(
            VoiceConsultSessionStatus,
            values_callable=enum_values,
            native_enum=False,
        ),
        default=VoiceConsultSessionStatus.IN_PROGRESS,
    )
    messages: Mapped[list] = mapped_column(JSON, nullable=False)
    final_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    patient_turns_completed: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    patient: Mapped["Patient"] = relationship("Patient", back_populates="voice_consult_sessions")
    appointment: Mapped["Appointment | None"] = relationship(
        "Appointment", back_populates="voice_consult_sessions"
    )
    prescriptions: Mapped[list["Prescription"]] = relationship(
        "Prescription", back_populates="voice_consult_session"
    )
