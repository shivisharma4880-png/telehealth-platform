from fastapi import APIRouter, Depends, HTTPException, Query, Request, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timezone, timedelta, date
from app.core.database import get_db
from app.core.deps import get_current_admin
from app.models.user import User, UserRole
from app.models.practitioner import Practitioner
from app.models.patient import Patient
from app.models.appointment import Appointment, AppointmentStatus
from app.models.organization import Organization
from app.models.audit import AuditEvent
from app.models.slot import Slot, SlotStatus
from app.models.encounter import Encounter, EncounterStatus
from app.models.medication import Prescription
from app.schemas.practitioner import PractitionerCreate, PractitionerOut, PractitionerUpdate
from app.schemas.admin import AppointmentCancelIn, AdminSummaryListOut, AdminSummaryRow, AdminAppointmentListOut
from app.core.security import hash_password
from app.services.audit_service import log_event
from typing import Optional, List
import uuid
import io
import csv

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/clinicians", response_model=PractitionerOut, status_code=201, summary="Invite/create a clinician")
async def create_clinician(
    body: PractitionerCreate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    reg_existing = await db.execute(
        select(Practitioner).where(Practitioner.registration_number == body.registration_number)
    )
    if reg_existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Registration number already exists")

    # Get admin's organization
    admin_prac = await db.execute(select(Practitioner).where(Practitioner.user_id == current_admin.id))
    org_id = None

    org_res = await db.execute(select(Organization).limit(1))
    org = org_res.scalar_one_or_none()
    if org:
        org_id = org.id

    user = User(
        id=str(uuid.uuid4()),
        email=body.email,
        hashed_password=hash_password(body.password),
        role=UserRole.CLINICIAN,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()

    practitioner = Practitioner(
        id=str(uuid.uuid4()),
        user_id=user.id,
        organization_id=org_id,
        first_name=body.first_name,
        last_name=body.last_name,
        registration_number=body.registration_number,
        specialty=body.specialty,
        languages=body.languages,
        consultation_fee=body.consultation_fee,
        bio=body.bio,
        years_of_experience=body.years_of_experience,
        slot_duration_minutes=body.slot_duration_minutes,
        buffer_minutes=body.buffer_minutes,
    )
    db.add(practitioner)
    await db.commit()
    await db.refresh(practitioner)
    return practitioner


@router.get("/clinicians", response_model=List[PractitionerOut])
async def list_clinicians(
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Practitioner))
    return result.scalars().all()


@router.put("/clinicians/{practitioner_id}", response_model=PractitionerOut)
async def update_clinician(
    practitioner_id: str,
    body: PractitionerUpdate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Practitioner).where(Practitioner.id == practitioner_id))
    practitioner = result.scalar_one_or_none()
    if not practitioner:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(practitioner, field, value)
    await db.commit()
    await db.refresh(practitioner)
    return practitioner


@router.delete("/clinicians/{practitioner_id}", summary="Deactivate clinician (soft remove)")
async def deactivate_clinician(
    practitioner_id: str,
    request: Request,
    force: bool = Query(False, description="Allow deactivation despite upcoming appointments"),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Practitioner).where(Practitioner.id == practitioner_id))
    practitioner = result.scalar_one_or_none()
    if not practitioner:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    now = datetime.now(timezone.utc)
    upcoming = await db.execute(
        select(func.count(Appointment.id))
        .select_from(Appointment)
        .join(Slot, Appointment.slot_id == Slot.id)
        .where(
            Appointment.practitioner_id == practitioner_id,
            Appointment.status.in_(
                (
                    AppointmentStatus.BOOKED,
                    AppointmentStatus.CONFIRMED,
                    AppointmentStatus.IN_PROGRESS,
                )
            ),
            Slot.start_time > now,
        )
    )
    upcoming_count = upcoming.scalar_one() or 0
    if upcoming_count > 0 and not force:
        raise HTTPException(
            status_code=400,
            detail="Clinician has upcoming appointments; cancel or reschedule them first, or pass force=true",
        )

    user = await db.get(User, practitioner.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found for practitioner")

    user.is_active = False
    practitioner.is_available = False
    await log_event(
        db,
        "clinician_deactivated",
        user_id=current_admin.id,
        resource_type="practitioner",
        resource_id=practitioner_id,
        description=f"Admin deactivated clinician {practitioner.full_name}",
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return {"message": "Clinician deactivated", "practitioner_id": practitioner_id}


@router.get("/organization", summary="Get clinic/organization settings")
async def get_organization(
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Organization).limit(1))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {
        "id": org.id, "name": org.name, "slug": org.slug, "address": org.address,
        "phone": org.phone, "email": org.email, "logo_url": org.logo_url,
        "branding_color": org.branding_color, "registration_number": org.registration_number,
        "cancellation_policy_hours": org.cancellation_policy_hours, "settings": org.settings,
    }


@router.put("/organization", summary="Update clinic settings")
async def update_organization(
    data: dict,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Organization).limit(1))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    allowed_fields = {"name", "address", "phone", "email", "branding_color", "cancellation_policy_hours", "settings"}
    for field, value in data.items():
        if field in allowed_fields:
            setattr(org, field, value)
    await db.commit()
    return {"message": "Organization updated"}


def _parse_slot_filter_datetime(value: str, *, is_end: bool) -> datetime:
    value = value.strip()
    try:
        if "T" in value or len(value) > 10:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        d = date.fromisoformat(value)
        if is_end:
            return datetime(d.year, d.month, d.day, 23, 59, 59, 999999, tzinfo=timezone.utc)
        return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date/datetime: {value!r}")


@router.get("/appointments", response_model=AdminAppointmentListOut, summary="Get all appointments for admin")
async def list_all_appointments(
    status: Optional[AppointmentStatus] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    filters = []
    if status:
        filters.append(Appointment.status == status)
    if date_from:
        filters.append(Slot.start_time >= _parse_slot_filter_datetime(date_from, is_end=False))
    if date_to:
        filters.append(Slot.start_time <= _parse_slot_filter_datetime(date_to, is_end=True))

    count_stmt = (
        select(func.count(Appointment.id))
        .select_from(Appointment)
        .join(Slot, Appointment.slot_id == Slot.id)
    )
    if filters:
        count_stmt = count_stmt.where(and_(*filters))
    total_res = await db.execute(count_stmt)
    total = int(total_res.scalar_one() or 0)

    list_stmt = (
        select(Appointment)
        .join(Slot, Appointment.slot_id == Slot.id)
        .order_by(Slot.start_time.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    if filters:
        list_stmt = list_stmt.where(and_(*filters))

    result = await db.execute(list_stmt)
    appointments = result.scalars().all()

    enriched = []
    for appt in appointments:
        prac = await db.get(Practitioner, appt.practitioner_id)
        pat = await db.get(Patient, appt.patient_id)
        slot = await db.get(Slot, appt.slot_id)
        enc_res = await db.execute(select(Encounter).where(Encounter.appointment_id == appt.id))
        enc = enc_res.scalar_one_or_none()
        enriched.append(
            {
                "id": appt.id,
                "status": appt.status.value,
                "payment_status": appt.payment_status.value,
                "amount_paid": float(appt.amount_paid),
                "created_at": appt.created_at.isoformat(),
                "practitioner_name": prac.full_name if prac else None,
                "patient_name": pat.full_name if pat else None,
                "slot_start": slot.start_time.isoformat() if slot else None,
                "slot_end": slot.end_time.isoformat() if slot else None,
                "chief_complaint": appt.chief_complaint,
                "encounter_id": enc.id if enc else None,
            }
        )
    return AdminAppointmentListOut(items=enriched, total=total)


@router.post("/appointments/{appointment_id}/cancel", summary="Cancel appointment (admin)")
async def admin_cancel_appointment(
    appointment_id: str,
    request: Request,
    body: AppointmentCancelIn = Body(default_factory=AppointmentCancelIn),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appt = result.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if appt.status in (
        AppointmentStatus.COMPLETED,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.NO_SHOW,
    ):
        raise HTTPException(status_code=400, detail="Appointment cannot be cancelled in its current status")

    slot = await db.get(Slot, appt.slot_id)
    if slot:
        slot.status = SlotStatus.AVAILABLE

    enc_res = await db.execute(select(Encounter).where(Encounter.appointment_id == appt.id))
    enc = enc_res.scalar_one_or_none()
    if enc and enc.status != EncounterStatus.COMPLETED:
        enc.status = EncounterStatus.CANCELLED

    appt.status = AppointmentStatus.CANCELLED
    if body.cancellation_reason is not None:
        appt.cancellation_reason = body.cancellation_reason[:500]

    await log_event(
        db,
        "appointment_cancelled_admin",
        user_id=current_admin.id,
        resource_type="appointment",
        resource_id=appointment_id,
        description="Admin cancelled appointment",
        metadata={"cancellation_reason": appt.cancellation_reason},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    await db.refresh(appt)
    return {"id": appt.id, "status": appt.status.value, "message": "Appointment cancelled"}


@router.get("/summaries", response_model=AdminSummaryListOut, summary="List visit records / summaries (admin)")
async def list_admin_summaries(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    total_res = await db.execute(select(func.count(Prescription.id)))
    total = int(total_res.scalar_one() or 0)

    rx_res = await db.execute(
        select(Prescription)
        .order_by(Prescription.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    prescriptions = rx_res.scalars().all()

    items: List[AdminSummaryRow] = []
    for rx in prescriptions:
        pat = await db.get(Patient, rx.patient_id)
        prac = await db.get(Practitioner, rx.practitioner_id) if rx.practitioner_id else None
        items.append(
            AdminSummaryRow(
                id=rx.id,
                patient_name=pat.full_name if pat else None,
                practitioner_name=prac.full_name if prac else None,
                diagnosis=rx.diagnosis,
                notes=rx.notes,
                status=rx.status,
                encounter_id=rx.encounter_id,
                created_at=rx.created_at,
            )
        )
    return AdminSummaryListOut(items=items, total=total)


@router.get("/dashboard", summary="Dashboard metrics")
async def get_dashboard(
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    today = datetime.now(timezone.utc).date()
    week_ago = today - timedelta(days=7)

    total_res = await db.execute(select(func.count(Appointment.id)))
    total = total_res.scalar_one() or 0

    completed_res = await db.execute(
        select(func.count(Appointment.id)).where(Appointment.status == AppointmentStatus.COMPLETED)
    )
    completed = completed_res.scalar_one() or 0

    no_show_res = await db.execute(
        select(func.count(Appointment.id)).where(Appointment.status == AppointmentStatus.NO_SHOW)
    )
    no_shows = no_show_res.scalar_one() or 0

    revenue_res = await db.execute(
        select(func.sum(Appointment.amount_paid))
    )
    total_revenue = float(revenue_res.scalar_one() or 0)

    patient_count_res = await db.execute(select(func.count(Patient.id)))
    patient_count = patient_count_res.scalar_one() or 0

    clinician_count_res = await db.execute(select(func.count(Practitioner.id)))
    clinician_count = clinician_count_res.scalar_one() or 0

    no_show_rate = (no_shows / total * 100) if total > 0 else 0

    return {
        "total_appointments": total,
        "completed_consultations": completed,
        "no_show_count": no_shows,
        "no_show_rate": round(no_show_rate, 1),
        "total_revenue_inr": total_revenue,
        "total_patients": patient_count,
        "total_clinicians": clinician_count,
    }


@router.get("/appointments/export", summary="Export appointments as CSV")
async def export_appointments(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(Appointment).order_by(Appointment.created_at.desc())
    result = await db.execute(query)
    appointments = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Patient", "Doctor", "Status", "Payment Status",
        "Amount Paid (INR)", "Created At"
    ])

    for appt in appointments:
        prac = await db.get(Practitioner, appt.practitioner_id)
        pat = await db.get(Patient, appt.patient_id)
        writer.writerow([
            appt.id,
            pat.full_name if pat else "N/A",
            prac.full_name if prac else "N/A",
            appt.status.value,
            appt.payment_status.value,
            float(appt.amount_paid),
            appt.created_at.isoformat(),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=appointments_export.csv"},
    )


@router.get("/audit-logs", summary="View audit log (admin only)")
async def get_audit_logs(
    event_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(AuditEvent).order_by(AuditEvent.created_at.desc())
    if event_type:
        query = query.where(AuditEvent.event_type == event_type)
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    events = result.scalars().all()

    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "user_id": e.user_id,
            "resource_type": e.resource_type,
            "resource_id": e.resource_id,
            "description": e.description,
            "ip_address": e.ip_address,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]
