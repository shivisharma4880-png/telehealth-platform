from pydantic import BaseModel, EmailStr
from typing import Optional, List
from app.models.practitioner import Specialty


class PractitionerCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    registration_number: str
    specialty: Specialty
    languages: List[str] = ["en"]
    consultation_fee: float = 0.0
    bio: Optional[str] = None
    years_of_experience: int = 0
    slot_duration_minutes: int = 15
    buffer_minutes: int = 5


class PractitionerUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    specialty: Optional[Specialty] = None
    languages: Optional[List[str]] = None
    consultation_fee: Optional[float] = None
    bio: Optional[str] = None
    years_of_experience: Optional[int] = None
    practice_address: Optional[str] = None
    slot_duration_minutes: Optional[int] = None
    buffer_minutes: Optional[int] = None
    is_available: Optional[bool] = None


class PractitionerOut(BaseModel):
    id: str
    user_id: str
    first_name: str
    last_name: str
    registration_number: str
    specialty: Specialty
    languages: List[str]
    consultation_fee: float
    bio: Optional[str] = None
    years_of_experience: int
    slot_duration_minutes: int
    buffer_minutes: int
    is_available: bool
    organization_id: Optional[str] = None
    model_config = {"from_attributes": True}


class SlotCreate(BaseModel):
    start_time: str  # ISO datetime string
    end_time: str


class SlotOut(BaseModel):
    id: str
    practitioner_id: str
    start_time: str
    end_time: str
    status: str
    model_config = {"from_attributes": True}
