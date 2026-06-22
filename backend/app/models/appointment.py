from __future__ import annotations
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum, JSON, Text, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.voice_consult_session import VoiceConsultSession
from app.core.database import Base
from app.core.sa_enum import enum_values


class AppointmentStatus(str, Enum):
    BOOKED = "booked"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    REFUNDED = "refunded"
    FAILED = "failed"


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), nullable=False)
    practitioner_id: Mapped[str] = mapped_column(String(36), ForeignKey("practitioners.id"), nullable=False)
    slot_id: Mapped[str] = mapped_column(String(36), ForeignKey("slots.id"), nullable=False, unique=True)
    dependent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("dependents.id"), nullable=True)
    status: Mapped[AppointmentStatus] = mapped_column(
        SAEnum(AppointmentStatus, name="appointmentstatus", values_callable=enum_values),
        default=AppointmentStatus.BOOKED,
    )
    chief_complaint: Mapped[str | None] = mapped_column(Text, nullable=True)
    questionnaire_answers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    payment_status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, name="paymentstatus", values_callable=enum_values),
        default=PaymentStatus.PENDING,
    )
    payment_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    amount_paid: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0)
    cancellation_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reminder_sent: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    patient: Mapped["Patient"] = relationship("Patient", back_populates="appointments")
    practitioner: Mapped["Practitioner"] = relationship("Practitioner", back_populates="appointments")
    slot: Mapped["Slot"] = relationship("Slot", back_populates="appointment")
    encounter: Mapped["Encounter | None"] = relationship("Encounter", back_populates="appointment", uselist=False)
    voice_consult_sessions: Mapped[list["VoiceConsultSession"]] = relationship(
        "VoiceConsultSession", back_populates="appointment"
    )


class QuestionnaireAnswer(Base):
    """Template questions per specialty."""
    __tablename__ = "questionnaire_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    specialty: Mapped[str] = mapped_column(String(50), nullable=False)
    questions: Mapped[list] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(default=1)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
