from __future__ import annotations
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum, JSON, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.sa_enum import enum_values

if TYPE_CHECKING:
    from app.models.voice_consult_session import VoiceConsultSession


class MedicationStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    STOPPED = "stopped"


class MedicationRequest(Base):
    """FHIR MedicationRequest-inspired model."""
    __tablename__ = "medication_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    prescription_id: Mapped[str] = mapped_column(String(36), ForeignKey("prescriptions.id"), nullable=False)
    drug_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("drug_formulary.id"), nullable=True)
    drug_name: Mapped[str] = mapped_column(String(255), nullable=False)
    strength: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dosage_form: Mapped[str | None] = mapped_column(String(100), nullable=True)
    route: Mapped[str] = mapped_column(String(50), default="oral")
    frequency: Mapped[str] = mapped_column(String(100), nullable=False)
    duration: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantity: Mapped[str | None] = mapped_column(String(100), nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[MedicationStatus] = mapped_column(
        SAEnum(MedicationStatus, name="medicationstatus", values_callable=enum_values),
        default=MedicationStatus.ACTIVE,
    )
    interaction_warnings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    prescription: Mapped["Prescription"] = relationship("Prescription", back_populates="medication_requests")
    drug: Mapped["DrugFormulary | None"] = relationship("DrugFormulary")


class Prescription(Base):
    __tablename__ = "prescriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    encounter_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("encounters.id"), nullable=True)
    practitioner_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("practitioners.id"), nullable=True)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), nullable=False)
    voice_consult_session_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("voice_consult_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="draft")
    diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_signed: Mapped[bool] = mapped_column(Boolean, default=False)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pdf_token: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    pdf_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    encounter: Mapped["Encounter | None"] = relationship("Encounter", back_populates="prescriptions")
    practitioner: Mapped["Practitioner | None"] = relationship("Practitioner", back_populates="prescriptions")
    voice_consult_session: Mapped["VoiceConsultSession | None"] = relationship(
        "VoiceConsultSession", back_populates="prescriptions"
    )
    medication_requests: Mapped[list["MedicationRequest"]] = relationship(
        "MedicationRequest", back_populates="prescription", cascade="all, delete-orphan"
    )
