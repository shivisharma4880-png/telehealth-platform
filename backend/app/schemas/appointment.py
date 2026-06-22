from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.models.appointment import AppointmentStatus, PaymentStatus


class AppointmentCreate(BaseModel):
    practitioner_id: str
    slot_id: str
    chief_complaint: str
    questionnaire_answers: Optional[Dict[str, Any]] = None
    dependent_id: Optional[str] = None


class AppointmentUpdate(BaseModel):
    status: Optional[AppointmentStatus] = None
    cancellation_reason: Optional[str] = None
    notes: Optional[str] = None


class PaymentInitiate(BaseModel):
    appointment_id: str
    amount: float
    currency: str = "INR"


class PaymentConfirm(BaseModel):
    appointment_id: str
    payment_reference: str
    amount_paid: float


class AppointmentOut(BaseModel):
    id: str
    patient_id: str
    practitioner_id: str
    slot_id: str
    status: AppointmentStatus
    chief_complaint: Optional[str] = None
    questionnaire_answers: Optional[Dict[str, Any]] = None
    payment_status: PaymentStatus
    payment_reference: Optional[str] = None
    amount_paid: float
    reminder_sent: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class AppointmentDetailOut(AppointmentOut):
    practitioner_name: Optional[str] = None
    patient_name: Optional[str] = None
    slot_start: Optional[datetime] = None
    slot_end: Optional[datetime] = None
    encounter_id: Optional[str] = None
