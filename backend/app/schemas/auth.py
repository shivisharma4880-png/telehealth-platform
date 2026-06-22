from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from app.models.user import UserRole


def normalize_phone(v: str) -> str:
    v = v.strip().replace(" ", "").replace("-", "")
    if not v.startswith("+"):
        v = "+91" + v.lstrip("0")
    return v


class OTPRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_phone(v)


class OTPVerify(BaseModel):
    phone: str
    otp: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_phone(v)


class EmailLogin(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: UserRole
    is_active: bool
    is_verified: bool

    model_config = {"from_attributes": True}


class TOTPSetupResponse(BaseModel):
    secret: str
    qr_code_url: str
    backup_codes: list[str]


class TOTPVerifyRequest(BaseModel):
    totp_code: str
