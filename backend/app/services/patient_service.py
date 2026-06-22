"""Patient profile helpers shared by auth and patient-scoped APIs."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient
from app.models.user import User


async def ensure_patient_record(
    db: AsyncSession,
    user: User,
    *,
    first_name: str | None = None,
    last_name: str | None = None,
) -> Patient:
    """Return existing Patient or create a minimal row (required for consent, bookings, etc.)."""
    r = await db.execute(select(Patient).where(Patient.user_id == user.id))
    existing = r.scalar_one_or_none()
    if existing:
        return existing

    first = (first_name or "").strip() or "Patient"
    last = (last_name or "").strip()
    patient = Patient(
        id=str(uuid.uuid4()),
        user_id=user.id,
        first_name=first[:100],
        last_name=last[:100] if last else "",
        preferred_language="en",
    )
    db.add(patient)
    await db.flush()
    return patient
