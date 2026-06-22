from __future__ import annotations
import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum, JSON, Text, Integer, Boolean, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.sa_enum import enum_values


class EncounterStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class NoteStatus(str, Enum):
    DRAFT = "draft"
    FINAL = "final"


class Encounter(Base):
    __tablename__ = "encounters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    appointment_id: Mapped[str] = mapped_column(String(36), ForeignKey("appointments.id"), unique=True, nullable=False)
    practitioner_id: Mapped[str] = mapped_column(String(36), ForeignKey("practitioners.id"), nullable=False)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), nullable=False)
    status: Mapped[EncounterStatus] = mapped_column(
        SAEnum(EncounterStatus, name="encounterstatus", values_callable=enum_values),
        default=EncounterStatus.SCHEDULED,
    )

    # Call / session metadata
    call_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    call_ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    call_quality_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Transcription
    full_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcription_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # SOAP Notes
    soap_note_status: Mapped[NoteStatus] = mapped_column(
        SAEnum(NoteStatus, name="notestatus", values_callable=enum_values),
        default=NoteStatus.DRAFT,
    )
    soap_subjective: Mapped[str | None] = mapped_column(Text, nullable=True)
    soap_objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    soap_assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    soap_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    soap_generated_count: Mapped[int] = mapped_column(Integer, default=0)
    soap_finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    diagnosis_codes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    investigations: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Vitals (if recorded)
    vitals: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    appointment: Mapped["Appointment"] = relationship("Appointment", back_populates="encounter")
    practitioner: Mapped["Practitioner"] = relationship("Practitioner", back_populates="encounters")
    transcript_segments: Mapped[list["TranscriptSegment"]] = relationship(
        "TranscriptSegment", back_populates="encounter", order_by="TranscriptSegment.created_at"
    )
    prescriptions: Mapped[list["Prescription"]] = relationship("Prescription", back_populates="encounter")


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    encounter_id: Mapped[str] = mapped_column(String(36), ForeignKey("encounters.id"), nullable=False)
    speaker: Mapped[str] = mapped_column(String(50), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    start_offset_seconds: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    encounter: Mapped["Encounter"] = relationship("Encounter", back_populates="transcript_segments")
