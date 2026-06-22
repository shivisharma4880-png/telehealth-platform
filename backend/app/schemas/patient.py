from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from app.models.patient import Gender


class DependentCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    relationship_to_patient: str


class DependentOut(DependentCreate):
    id: str
    patient_id: str
    model_config = {"from_attributes": True}


class PatientProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    abha_id: Optional[str] = None
    preferred_language: Optional[str] = None
    allergies: Optional[List[str]] = None
    medical_history: Optional[str] = None


class PatientOut(BaseModel):
    id: str
    user_id: str
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    abha_id: Optional[str] = None
    preferred_language: str
    allergies: Optional[List[str]] = None
    medical_history: Optional[str] = None
    dependents: List[DependentOut] = []
    model_config = {"from_attributes": True}
