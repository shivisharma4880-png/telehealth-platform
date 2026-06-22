from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class MedicationRequestCreate(BaseModel):
    drug_id: Optional[str] = None
    drug_name: str
    strength: Optional[str] = None
    dosage_form: Optional[str] = None
    route: str = "oral"
    frequency: str
    duration: Optional[str] = None
    quantity: Optional[str] = None
    instructions: Optional[str] = None


class MedicationRequestOut(MedicationRequestCreate):
    id: str
    prescription_id: str
    status: str
    interaction_warnings: Optional[List[dict]] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class PrescriptionCreate(BaseModel):
    encounter_id: str
    diagnosis: Optional[str] = None
    notes: Optional[str] = None
    medications: List[MedicationRequestCreate]


class PrescriptionUpdate(BaseModel):
    diagnosis: Optional[str] = None
    notes: Optional[str] = None
    medications: Optional[List[MedicationRequestCreate]] = None


class PrescriptionOut(BaseModel):
    id: str
    encounter_id: Optional[str] = None
    practitioner_id: Optional[str] = None
    voice_consult_session_id: Optional[str] = None
    patient_id: str
    status: str
    diagnosis: Optional[str] = None
    notes: Optional[str] = None
    is_signed: bool
    signed_at: Optional[datetime] = None
    pdf_path: Optional[str] = None
    pdf_token: Optional[str] = None
    medication_requests: List[MedicationRequestOut] = []
    created_at: datetime
    model_config = {"from_attributes": True}


class DrugSearchResult(BaseModel):
    id: str
    name: str
    generic_name: Optional[str] = None
    brand_names: Optional[List[str]] = None
    drug_class: Optional[str] = None
    available_strengths: Optional[List[str]] = None
    dosage_forms: Optional[List[str]] = None
    is_controlled: bool
    model_config = {"from_attributes": True}


class InteractionCheckRequest(BaseModel):
    drug_ids: List[str]
    patient_allergies: Optional[List[str]] = None
