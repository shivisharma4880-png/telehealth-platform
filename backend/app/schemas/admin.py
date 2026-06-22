from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class AppointmentCancelIn(BaseModel):
    cancellation_reason: Optional[str] = None


class AdminSummaryRow(BaseModel):
    id: str
    patient_name: Optional[str] = None
    practitioner_name: Optional[str] = None
    diagnosis: Optional[str] = None
    notes: Optional[str] = None
    status: str
    encounter_id: Optional[str] = None
    created_at: datetime


class AdminSummaryListOut(BaseModel):
    items: List[AdminSummaryRow]
    total: int


class AdminAppointmentListOut(BaseModel):
    items: List[dict[str, Any]]
    total: int
