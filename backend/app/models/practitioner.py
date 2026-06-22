from __future__ import annotations
import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum, JSON, Numeric, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.sa_enum import enum_values


class Specialty(str, Enum):
    GENERAL_PRACTICE = "general_practice"
    DERMATOLOGY = "dermatology"
    MENTAL_HEALTH = "mental_health"
    PEDIATRICS = "pediatrics"
    CARDIOLOGY = "cardiology"
    ORTHOPEDICS = "orthopedics"
    OTHER = "other"


class Practitioner(Base):
    __tablename__ = "practitioners"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    organization_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    registration_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    specialty: Mapped[Specialty] = mapped_column(
        SAEnum(Specialty, name="specialty", values_callable=enum_values),
        nullable=False,
    )
    languages: Mapped[list] = mapped_column(JSON, nullable=False, default=lambda: ["en"])
    consultation_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    years_of_experience: Mapped[int] = mapped_column(Integer, default=0)
    practice_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    digital_signature_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    slot_duration_minutes: Mapped[int] = mapped_column(Integer, default=15)
    buffer_minutes: Mapped[int] = mapped_column(Integer, default=5)
    is_available: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship("User", back_populates="practitioner")
    organization: Mapped["Organization | None"] = relationship("Organization", back_populates="practitioners")
    slots: Mapped[list["Slot"]] = relationship("Slot", back_populates="practitioner")
    appointments: Mapped[list["Appointment"]] = relationship("Appointment", back_populates="practitioner")
    encounters: Mapped[list["Encounter"]] = relationship("Encounter", back_populates="practitioner")
    prescriptions: Mapped[list["Prescription"]] = relationship("Prescription", back_populates="practitioner")

    @property
    def full_name(self) -> str:
        return f"Dr. {self.first_name} {self.last_name}"
