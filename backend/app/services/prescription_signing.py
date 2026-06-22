"""Shared logic to sign a clinician prescription (PDF, token, audit, SMS)."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone, timedelta

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medication import Prescription, MedicationRequest
from app.models.organization import Organization
from app.models.patient import Patient
from app.models.practitioner import Practitioner
from app.models.user import User
from app.services.audit_service import log_event
from app.services.notification_service import notification_service
from app.services.pdf_service import generate_prescription_pdf


async def sign_prescription_entity(
    db: AsyncSession,
    prescription: Prescription,
    *,
    signing_user_id: str,
    request: Request | None = None,
) -> None:
    """
    Finalize a draft clinician prescription (PDF + signed flags).
    Caller must commit. Skips if already signed or not a clinician prescription.
    """
    if prescription.is_signed or prescription.practitioner_id is None:
        return

    practitioner = await db.get(Practitioner, prescription.practitioner_id)
    if not practitioner:
        return

    patient = await db.get(Patient, prescription.patient_id)
    org = await db.get(Organization, practitioner.organization_id) if practitioner.organization_id else None

    patient_user: User | None = None
    if patient:
        patient_user = await db.get(User, patient.user_id)

    med_res = await db.execute(
        select(MedicationRequest).where(MedicationRequest.prescription_id == prescription.id)
    )
    medications = med_res.scalars().all()

    age = "N/A"
    if patient and patient.date_of_birth:
        today = datetime.now().date()
        age = str(today.year - patient.date_of_birth.year)

    specialty_display = {
        "general_practice": "General Practitioner",
        "dermatology": "Dermatologist",
        "mental_health": "Psychiatrist / Mental Health Specialist",
        "pediatrics": "Pediatrician",
        "cardiology": "Cardiologist",
        "orthopedics": "Orthopedic Surgeon",
        "other": "Specialist",
    }.get(practitioner.specialty.value if practitioner.specialty else "", "Doctor")

    practitioner_data = {
        "full_name": practitioner.full_name,
        "specialty_display": specialty_display,
        "registration_number": practitioner.registration_number,
    }
    dob_str = "-"
    if patient and patient.date_of_birth:
        dob_str = patient.date_of_birth.strftime("%d/%m/%Y")

    patient_data = {
        "full_name": patient.full_name if patient else "Unknown",
        "age": age,
        "gender": patient.gender.value if patient and patient.gender else "N/A",
        "abha_id": patient.abha_id if patient else None,
        "phone": (patient_user.phone if patient_user and patient_user.phone else None) or "-",
        "date_of_birth": dob_str,
        "mrn": (patient.id.replace("-", "")[:16].upper() if patient else "-"),
        "address": "-",
    }
    org_data = {
        "name": org.name if org else "Medical Clinic",
        "address": org.address if org else "",
        "phone": org.phone if org else "",
        "email": org.email if org else "",
        "registration_number": org.registration_number if org else "",
    }
    meds_data = [
        {
            "drug_name": m.drug_name,
            "strength": m.strength,
            "dosage_form": m.dosage_form,
            "frequency": m.frequency,
            "duration": m.duration,
            "instructions": m.instructions,
            "interaction_warnings": m.interaction_warnings,
        }
        for m in medications
    ]

    pdf_path = generate_prescription_pdf(
        prescription_data={"id": prescription.id, "diagnosis": prescription.diagnosis, "notes": prescription.notes},
        practitioner_data=practitioner_data,
        patient_data=patient_data,
        organization_data=org_data,
        medications=meds_data,
    )

    share_token = secrets.token_hex(32)
    prescription.is_signed = True
    prescription.signed_at = datetime.now(timezone.utc)
    prescription.status = "signed"
    prescription.pdf_path = pdf_path
    prescription.pdf_token = share_token
    prescription.pdf_token_expires_at = datetime.now(timezone.utc) + timedelta(days=1)

    await log_event(
        db,
        "prescription_signed",
        user_id=signing_user_id,
        resource_type="prescription",
        resource_id=prescription.id,
        ip_address=request.client.host if request else None,
    )

    pat_user_res = await db.execute(
        select(User).join(Patient, User.id == Patient.user_id).where(Patient.id == prescription.patient_id)
    )
    pat_user = pat_user_res.scalar_one_or_none()
    if pat_user and pat_user.phone and patient:
        await notification_service.send_prescription_ready(pat_user.phone, patient.full_name)
