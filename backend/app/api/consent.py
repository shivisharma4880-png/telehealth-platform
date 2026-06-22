from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import get_current_patient
from app.models.user import User
from app.models.consent import Consent, ConsentVersion
from app.services.patient_service import ensure_patient_record
import uuid

router = APIRouter(prefix="/consent", tags=["Consent"])


@router.get("/versions", summary="Get active consent versions")
async def get_consent_versions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ConsentVersion).where(ConsentVersion.is_active == True)
    )
    versions = result.scalars().all()
    return [
        {
            "id": v.id,
            "consent_type": v.consent_type,
            "version": v.version,
            "title": v.title,
            "content": v.content,
        }
        for v in versions
    ]


@router.post("/accept", summary="Patient accepts consent version")
async def accept_consent(
    version_id: str,
    request: Request,
    current_user: User = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    version = await db.get(ConsentVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Consent version not found")

    patient = await ensure_patient_record(db, current_user)

    consent = Consent(
        id=str(uuid.uuid4()),
        patient_id=patient.id,
        version_id=version_id,
        accepted=True,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(consent)
    await db.commit()
    return {"message": "Consent recorded", "consent_id": consent.id}


@router.get("/my", summary="Get my consent history")
async def get_my_consents(
    current_user: User = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    patient = await ensure_patient_record(db, current_user)

    result = await db.execute(
        select(Consent).where(Consent.patient_id == patient.id)
    )
    consents = result.scalars().all()
    return [
        {"id": c.id, "version_id": c.version_id, "accepted": c.accepted, "accepted_at": c.accepted_at.isoformat()}
        for c in consents
    ]
