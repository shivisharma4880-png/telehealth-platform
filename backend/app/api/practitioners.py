from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timezone
from app.core.database import get_db
from app.core.deps import get_current_user, get_current_clinician, get_current_admin
from app.models.user import User, UserRole
from app.models.practitioner import Practitioner, Specialty
from app.models.slot import Slot, SlotStatus
from app.schemas.practitioner import PractitionerUpdate, PractitionerOut, SlotOut
from app.services.slot_availability import ensure_slots_in_utc_window, parse_slot_boundary
from typing import Optional, List
import uuid

router = APIRouter(prefix="/practitioners", tags=["Practitioners"])


@router.get("/", response_model=List[PractitionerOut], summary="List practitioners (public discovery)")
async def list_practitioners(
    specialty: Optional[Specialty] = Query(None),
    language: Optional[str] = Query(None),
    min_fee: Optional[float] = Query(None),
    max_fee: Optional[float] = Query(None),
    organization_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Practitioner).where(Practitioner.is_available == True)

    if specialty:
        query = query.where(Practitioner.specialty == specialty)
    if min_fee is not None:
        query = query.where(Practitioner.consultation_fee >= min_fee)
    if max_fee is not None:
        query = query.where(Practitioner.consultation_fee <= max_fee)
    if organization_id:
        query = query.where(Practitioner.organization_id == organization_id)

    result = await db.execute(query)
    practitioners = result.scalars().all()

    if language:
        practitioners = [p for p in practitioners if language in (p.languages or [])]

    return practitioners


@router.get("/me", response_model=PractitionerOut, summary="Get my practitioner profile")
async def get_my_profile(
    current_user: User = Depends(get_current_clinician),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Practitioner).where(Practitioner.user_id == current_user.id))
    practitioner = result.scalar_one_or_none()
    if not practitioner:
        raise HTTPException(status_code=404, detail="Practitioner profile not found")
    return practitioner


@router.put("/me", response_model=PractitionerOut)
async def update_my_profile(
    body: PractitionerUpdate,
    current_user: User = Depends(get_current_clinician),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Practitioner).where(Practitioner.user_id == current_user.id))
    practitioner = result.scalar_one_or_none()
    if not practitioner:
        raise HTTPException(status_code=404, detail="Practitioner profile not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(practitioner, field, value)
    await db.commit()
    await db.refresh(practitioner)
    return practitioner


@router.get("/{practitioner_id}", response_model=PractitionerOut)
async def get_practitioner(practitioner_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Practitioner).where(Practitioner.id == practitioner_id))
    practitioner = result.scalar_one_or_none()
    if not practitioner:
        raise HTTPException(status_code=404, detail="Practitioner not found")
    return practitioner


@router.get("/{practitioner_id}/slots", response_model=List[SlotOut], summary="Get available slots for a practitioner")
async def get_available_slots(
    practitioner_id: str,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    result_p = await db.execute(select(Practitioner).where(Practitioner.id == practitioner_id))
    practitioner = result_p.scalar_one_or_none()
    if not practitioner:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    dt_from: Optional[datetime] = None
    dt_to: Optional[datetime] = None
    if date_from:
        try:
            dt_from = parse_slot_boundary(date_from)
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = parse_slot_boundary(date_to)
        except ValueError:
            pass

    def slot_query():
        q = select(Slot).where(
            and_(
                Slot.practitioner_id == practitioner_id,
                Slot.status == SlotStatus.AVAILABLE,
                Slot.start_time > datetime.now(timezone.utc),
            )
        ).order_by(Slot.start_time)
        if dt_from is not None:
            q = q.where(Slot.start_time >= dt_from)
        if dt_to is not None:
            q = q.where(Slot.start_time < dt_to)
        return q

    result = await db.execute(slot_query())
    slots = result.scalars().all()

    if not slots and dt_from is not None and dt_to is not None:
        await ensure_slots_in_utc_window(db, practitioner, dt_from, dt_to)
        await db.commit()
        result = await db.execute(slot_query())
        slots = result.scalars().all()

    return [
        SlotOut(
            id=s.id,
            practitioner_id=s.practitioner_id,
            start_time=s.start_time.isoformat(),
            end_time=s.end_time.isoformat(),
            status=s.status.value,
        )
        for s in slots
    ]


@router.post("/me/slots/block", summary="Block a time slot")
async def block_slot(
    slot_id: str,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_clinician),
    db: AsyncSession = Depends(get_db),
):
    result_p = await db.execute(select(Practitioner).where(Practitioner.user_id == current_user.id))
    practitioner = result_p.scalar_one_or_none()
    if not practitioner:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    result_s = await db.execute(
        select(Slot).where(Slot.id == slot_id, Slot.practitioner_id == practitioner.id)
    )
    slot = result_s.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    if slot.status == SlotStatus.BOOKED:
        raise HTTPException(status_code=400, detail="Cannot block a booked slot")

    slot.status = SlotStatus.BLOCKED
    slot.is_blocked = True
    slot.block_reason = reason
    await db.commit()
    return {"message": "Slot blocked"}
