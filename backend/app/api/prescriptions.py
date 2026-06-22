from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
import uuid
import os

from app.core.database import get_db
from app.core.deps import get_current_user, get_current_clinician, get_current_patient
from app.models.user import User, UserRole
from app.models.medication import Prescription, MedicationRequest
from app.models.encounter import Encounter
from app.models.practitioner import Practitioner
from app.models.patient import Patient
from app.schemas.prescription import (
    PrescriptionCreate, PrescriptionUpdate, PrescriptionOut,
    MedicationRequestCreate, DrugSearchResult, InteractionCheckRequest
)
from app.services.drug_service import check_interactions, search_drugs
from app.services.audit_service import log_event
from app.services.prescription_signing import sign_prescription_entity
from app.models.drug import DrugFormulary
from typing import List, Optional

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"])


@router.get("/drugs/search", response_model=List[DrugSearchResult], summary="Search drug formulary")
async def search_drug_formulary(
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_db),
):
    drugs = await search_drugs(db, q)
    return drugs


@router.post("/drugs/check-interactions", summary="Check drug interactions and allergy conflicts")
async def check_drug_interactions(
    body: InteractionCheckRequest,
    current_user: User = Depends(get_current_clinician),
    db: AsyncSession = Depends(get_db),
):
    # Get drug names for allergy check
    drug_names = []
    for drug_id in body.drug_ids:
        drug = await db.get(DrugFormulary, drug_id)
        if drug:
            drug_names.append(drug.name)

    warnings = await check_interactions(db, body.drug_ids, body.patient_allergies, drug_names)
    return {"warnings": warnings, "count": len(warnings)}


@router.post("/", response_model=PrescriptionOut, status_code=201, summary="Create a prescription")
async def create_prescription(
    body: PrescriptionCreate,
    request: Request,
    current_user: User = Depends(get_current_clinician),
    db: AsyncSession = Depends(get_db),
):
    # Validate encounter
    enc_res = await db.execute(select(Encounter).where(Encounter.id == body.encounter_id))
    encounter = enc_res.scalar_one_or_none()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")

    prac_res = await db.execute(select(Practitioner).where(Practitioner.user_id == current_user.id))
    practitioner = prac_res.scalar_one_or_none()
    if not practitioner or practitioner.id != encounter.practitioner_id:
        raise HTTPException(status_code=403, detail="Not authorized for this encounter")

    # Create prescription
    prescription = Prescription(
        id=str(uuid.uuid4()),
        encounter_id=body.encounter_id,
        practitioner_id=practitioner.id,
        patient_id=encounter.patient_id,
        status="draft",
        diagnosis=body.diagnosis,
        notes=body.notes,
    )
    db.add(prescription)
    await db.flush()

    # Add medications with interaction checks
    drug_ids = [m.drug_id for m in body.medications if m.drug_id]
    pat_res = await db.execute(select(Patient).where(Patient.id == encounter.patient_id))
    patient = pat_res.scalar_one_or_none()
    patient_allergies = patient.allergies if patient else None
    drug_names = [m.drug_name for m in body.medications]

    warnings = await check_interactions(db, drug_ids, patient_allergies, drug_names)
    warning_by_drug: dict = {}
    for w in warnings:
        key = w.get("drug_a") or w.get("drug")
        if key:
            if key not in warning_by_drug:
                warning_by_drug[key] = []
            warning_by_drug[key].append(w)

    for med_data in body.medications:
        med_warnings = warning_by_drug.get(med_data.drug_name, [])
        med = MedicationRequest(
            id=str(uuid.uuid4()),
            prescription_id=prescription.id,
            **med_data.model_dump(),
            interaction_warnings=med_warnings if med_warnings else None,
        )
        db.add(med)

    await log_event(db, "prescription_created", user_id=current_user.id, resource_type="prescription",
                    resource_id=prescription.id, ip_address=request.client.host if request.client else None)
    await db.commit()
    await db.refresh(prescription)
    return prescription


@router.post("/{prescription_id}/sign", response_model=PrescriptionOut, summary="Sign and generate prescription PDF")
async def sign_prescription(
    prescription_id: str,
    request: Request,
    current_user: User = Depends(get_current_clinician),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Prescription).where(Prescription.id == prescription_id))
    prescription = result.scalar_one_or_none()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")

    if prescription.practitioner_id is None:
        raise HTTPException(
            status_code=400,
            detail="AI voice consult records cannot be e-signed. They are for your records only.",
        )

    prac_res = await db.execute(select(Practitioner).where(Practitioner.user_id == current_user.id))
    practitioner = prac_res.scalar_one_or_none()
    if not practitioner or practitioner.id != prescription.practitioner_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if prescription.is_signed:
        raise HTTPException(status_code=400, detail="Prescription already signed")

    await sign_prescription_entity(
        db,
        prescription,
        signing_user_id=current_user.id,
        request=request,
    )
    await db.commit()
    await db.refresh(prescription)

    return prescription


@router.get("/download/{token}", summary="Download prescription PDF via secure token")
async def download_prescription(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prescription).where(Prescription.pdf_token == token))
    prescription = result.scalar_one_or_none()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found or invalid token")

    if prescription.pdf_token_expires_at and prescription.pdf_token_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Download link expired")

    if not prescription.pdf_path or not os.path.exists(prescription.pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")

    return FileResponse(
        prescription.pdf_path,
        media_type="application/pdf",
        filename=(
            f"ai_visit_summary_{prescription.id[:8]}.pdf"
            if prescription.status == "ai_consult_record"
            else f"prescription_{prescription.id[:8]}.pdf"
        ),
    )


@router.get("/my", response_model=List[PrescriptionOut], summary="Get my prescriptions (patient)")
async def get_my_prescriptions(
    current_user: User = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    pat_res = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
    patient = pat_res.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    result = await db.execute(
        select(Prescription)
        .options(selectinload(Prescription.medication_requests))
        .where(Prescription.patient_id == patient.id)
        .order_by(Prescription.created_at.desc())
    )
    return result.scalars().unique().all()


@router.get("/{prescription_id}", response_model=PrescriptionOut)
async def get_prescription(
    prescription_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Prescription).where(Prescription.id == prescription_id))
    prescription = result.scalar_one_or_none()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return prescription
