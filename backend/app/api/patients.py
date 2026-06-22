from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import get_current_patient, get_current_user, get_clinician_or_admin
from app.models.user import User, UserRole
from app.models.patient import Patient, Dependent
from app.schemas.patient import PatientProfileUpdate, PatientOut, DependentCreate, DependentOut
import uuid

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.get("/me", response_model=PatientOut)
async def get_my_profile(
    current_user: User = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Patient).where(Patient.user_id == current_user.id)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    return patient


@router.put("/me", response_model=PatientOut)
async def update_my_profile(
    body: PatientProfileUpdate,
    current_user: User = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(patient, field, value)
    await db.commit()
    await db.refresh(patient)
    return patient


@router.get("/me/dependents", response_model=list[DependentOut])
async def get_dependents(
    current_user: User = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    dep_result = await db.execute(select(Dependent).where(Dependent.patient_id == patient.id))
    return dep_result.scalars().all()


@router.post("/me/dependents", response_model=DependentOut, status_code=201)
async def add_dependent(
    body: DependentCreate,
    current_user: User = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    dependent = Dependent(id=str(uuid.uuid4()), patient_id=patient.id, **body.model_dump())
    db.add(dependent)
    await db.commit()
    await db.refresh(dependent)
    return dependent


@router.delete("/me/dependents/{dependent_id}", status_code=204)
async def delete_dependent(
    dependent_id: str,
    current_user: User = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    dep_result = await db.execute(
        select(Dependent).where(Dependent.id == dependent_id, Dependent.patient_id == patient.id)
    )
    dependent = dep_result.scalar_one_or_none()
    if not dependent:
        raise HTTPException(status_code=404, detail="Dependent not found")

    await db.delete(dependent)
    await db.commit()


@router.get("/{patient_id}", response_model=PatientOut)
async def get_patient_by_id(
    patient_id: str,
    current_user: User = Depends(get_clinician_or_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient
