from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timezone
from app.core.database import get_db
from app.core.deps import get_current_user, get_current_patient, get_current_clinician, get_clinician_or_admin
from app.models.user import User, UserRole
from app.models.patient import Patient
from app.models.practitioner import Practitioner
from app.models.slot import Slot, SlotStatus
from app.models.appointment import Appointment, AppointmentStatus, PaymentStatus
from app.models.encounter import Encounter, EncounterStatus
from app.schemas.appointment import (
    AppointmentCreate, AppointmentUpdate, AppointmentOut,
    AppointmentDetailOut, PaymentInitiate, PaymentConfirm
)
from app.services.notification_service import notification_service
from app.services.payment_service import payment_service
from app.services.audit_service import log_event
from typing import Optional, List
import uuid

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.post("/", response_model=AppointmentOut, status_code=201, summary="Book an appointment")
async def book_appointment(
    body: AppointmentCreate,
    request: Request,
    current_user: User = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    # Get patient
    result = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    # Get slot
    result = await db.execute(select(Slot).where(Slot.id == body.slot_id))
    slot = result.scalar_one_or_none()
    if not slot or slot.status != SlotStatus.AVAILABLE:
        raise HTTPException(status_code=400, detail="Slot not available")

    # Verify practitioner
    result = await db.execute(select(Practitioner).where(Practitioner.id == body.practitioner_id))
    practitioner = result.scalar_one_or_none()
    if not practitioner:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    if slot.practitioner_id != practitioner.id:
        raise HTTPException(status_code=400, detail="Slot does not belong to this practitioner")

    # Create appointment
    appointment = Appointment(
        id=str(uuid.uuid4()),
        patient_id=patient.id,
        practitioner_id=practitioner.id,
        slot_id=slot.id,
        dependent_id=body.dependent_id,
        chief_complaint=body.chief_complaint,
        questionnaire_answers=body.questionnaire_answers,
        status=AppointmentStatus.BOOKED,
        payment_status=PaymentStatus.PENDING if practitioner.consultation_fee > 0 else PaymentStatus.PAID,
        amount_paid=0.0 if practitioner.consultation_fee > 0 else 0.0,
    )
    db.add(appointment)

    # Mark slot as booked
    slot.status = SlotStatus.BOOKED

    # Create encounter record
    encounter = Encounter(
        id=str(uuid.uuid4()),
        appointment_id=appointment.id,
        practitioner_id=practitioner.id,
        patient_id=patient.id,
        status=EncounterStatus.SCHEDULED,
    )
    db.add(encounter)

    await log_event(
        db, "appointment_booked",
        user_id=current_user.id,
        resource_type="appointment",
        resource_id=appointment.id,
        description=f"Patient {patient.full_name} booked appointment with {practitioner.full_name}",
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    # Send confirmation notification
    if current_user.phone:
        await notification_service.send_appointment_confirmation(
            current_user.phone,
            patient.full_name,
            practitioner.full_name,
            slot.start_time.strftime("%d %b %Y at %I:%M %p"),
        )

    return appointment


@router.get("/my", response_model=List[AppointmentDetailOut], summary="Get my appointments (patient)")
async def get_my_appointments(
    status: Optional[AppointmentStatus] = Query(None),
    current_user: User = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    result_p = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
    patient = result_p.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    query = select(Appointment).where(Appointment.patient_id == patient.id)
    if status:
        query = query.where(Appointment.status == status)
    query = query.order_by(Appointment.created_at.desc())

    result = await db.execute(query)
    appointments = result.scalars().all()

    details = []
    for appt in appointments:
        prac_res = await db.execute(select(Practitioner).where(Practitioner.id == appt.practitioner_id))
        prac = prac_res.scalar_one_or_none()
        slot_res = await db.execute(select(Slot).where(Slot.id == appt.slot_id))
        slot = slot_res.scalar_one_or_none()
        enc_res = await db.execute(select(Encounter).where(Encounter.appointment_id == appt.id))
        enc = enc_res.scalar_one_or_none()

        detail = AppointmentDetailOut(
            **AppointmentOut.model_validate(appt).model_dump(),
            practitioner_name=prac.full_name if prac else None,
            patient_name=patient.full_name,
            slot_start=slot.start_time if slot else None,
            slot_end=slot.end_time if slot else None,
            encounter_id=enc.id if enc else None,
        )
        details.append(detail)
    return details


@router.get("/schedule", response_model=List[AppointmentDetailOut], summary="Get clinician schedule")
async def get_clinician_schedule(
    date: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    status: Optional[AppointmentStatus] = Query(None),
    current_user: User = Depends(get_current_clinician),
    db: AsyncSession = Depends(get_db),
):
    result_p = await db.execute(select(Practitioner).where(Practitioner.user_id == current_user.id))
    practitioner = result_p.scalar_one_or_none()
    if not practitioner:
        raise HTTPException(status_code=404, detail="Practitioner not found")

    query = select(Appointment).where(Appointment.practitioner_id == practitioner.id)
    if status:
        query = query.where(Appointment.status == status)

    result = await db.execute(query)
    appointments = result.scalars().all()

    details = []
    for appt in appointments:
        slot_res = await db.execute(select(Slot).where(Slot.id == appt.slot_id))
        slot = slot_res.scalar_one_or_none()

        if date and slot:
            try:
                filter_date = datetime.fromisoformat(date).date()
                if slot.start_time.date() != filter_date:
                    continue
            except ValueError:
                pass

        pat_res = await db.execute(select(Patient).where(Patient.id == appt.patient_id))
        patient = pat_res.scalar_one_or_none()
        enc_res = await db.execute(select(Encounter).where(Encounter.appointment_id == appt.id))
        enc = enc_res.scalar_one_or_none()

        detail = AppointmentDetailOut(
            **AppointmentOut.model_validate(appt).model_dump(),
            practitioner_name=practitioner.full_name,
            patient_name=patient.full_name if patient else None,
            slot_start=slot.start_time if slot else None,
            slot_end=slot.end_time if slot else None,
            encounter_id=enc.id if enc else None,
        )
        details.append(detail)

    details.sort(key=lambda x: x.slot_start or datetime.min.replace(tzinfo=timezone.utc))
    return details


@router.get("/{appointment_id}", response_model=AppointmentDetailOut)
async def get_appointment(
    appointment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appt = result.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    prac_res = await db.execute(select(Practitioner).where(Practitioner.id == appt.practitioner_id))
    prac = prac_res.scalar_one_or_none()
    pat_res = await db.execute(select(Patient).where(Patient.id == appt.patient_id))
    patient = pat_res.scalar_one_or_none()
    slot_res = await db.execute(select(Slot).where(Slot.id == appt.slot_id))
    slot = slot_res.scalar_one_or_none()
    enc_res = await db.execute(select(Encounter).where(Encounter.appointment_id == appt.id))
    enc = enc_res.scalar_one_or_none()

    return AppointmentDetailOut(
        **AppointmentOut.model_validate(appt).model_dump(),
        practitioner_name=prac.full_name if prac else None,
        patient_name=patient.full_name if patient else None,
        slot_start=slot.start_time if slot else None,
        slot_end=slot.end_time if slot else None,
        encounter_id=enc.id if enc else None,
    )


@router.patch("/{appointment_id}", response_model=AppointmentOut)
async def update_appointment(
    appointment_id: str,
    body: AppointmentUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appt = result.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(appt, field, value)

    await log_event(db, "appointment_updated", user_id=current_user.id, resource_type="appointment",
                    resource_id=appointment_id, metadata=body.model_dump(exclude_none=True))
    await db.commit()
    await db.refresh(appt)
    return appt


@router.post("/payment/initiate", summary="Initiate payment for appointment")
async def initiate_payment(
    body: PaymentInitiate,
    current_user: User = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Appointment).where(Appointment.id == body.appointment_id))
    appt = result.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    order = await payment_service.create_order(body.amount, body.currency, body.appointment_id)
    return order


@router.post("/payment/confirm", summary="Confirm payment after Razorpay callback")
async def confirm_payment(
    body: PaymentConfirm,
    current_user: User = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Appointment).where(Appointment.id == body.appointment_id))
    appt = result.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appt.payment_status = PaymentStatus.PAID
    appt.payment_reference = body.payment_reference
    appt.amount_paid = body.amount_paid
    await db.commit()
    return {"message": "Payment confirmed", "appointment_id": appt.id}
