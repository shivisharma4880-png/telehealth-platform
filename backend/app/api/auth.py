from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from slowapi import Limiter
from slowapi.util import get_remote_address
import uuid

from app.core.database import get_db

limiter = Limiter(key_func=get_remote_address)
from app.core.security import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, decode_refresh_token, generate_otp
)
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.services.patient_service import ensure_patient_record
from app.schemas.auth import (
    OTPRequest, OTPVerify, EmailLogin, TokenResponse,
    RefreshRequest, UserOut, TOTPSetupResponse, TOTPVerifyRequest
)
from app.services.audit_service import log_event
from app.services.notification_service import notification_service
import pyotp
import qrcode
import io
import base64

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/otp/request", summary="Request OTP for patient login")
@limiter.limit("5/minute")
async def request_otp(body: OTPRequest, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.phone == body.phone))
    user = result.scalar_one_or_none()

    otp = generate_otp()
    expires = datetime.now(timezone.utc) + timedelta(minutes=10)

    if not user:
        user = User(
            id=str(uuid.uuid4()),
            phone=body.phone,
            role=UserRole.PATIENT,
            is_active=True,
            is_verified=False,
            otp_code=otp,
            otp_expires_at=expires,
        )
        db.add(user)
    else:
        user.otp_code = otp
        user.otp_expires_at = expires

    await db.commit()

    await notification_service.send_otp_sms(body.phone, otp)
    return {"message": "OTP sent successfully", "expires_in_minutes": 10}


@router.post("/otp/verify", response_model=TokenResponse, summary="Verify OTP and login/register patient")
async def verify_otp(body: OTPVerify, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.phone == body.phone))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phone number not found. Request OTP first.")

    if not user.otp_code or user.otp_code != body.otp:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP")

    if user.otp_expires_at and user.otp_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="OTP expired")

    user.otp_code = None
    user.otp_expires_at = None
    user.is_verified = True

    await ensure_patient_record(
        db, user, first_name=body.first_name, last_name=body.last_name
    )

    await db.commit()

    access_token = create_access_token({"sub": user.id, "role": user.role.value})
    refresh_token = create_refresh_token({"sub": user.id})

    await log_event(db, "user_login", user_id=user.id, description="Patient OTP login",
                    ip_address=request.client.host if request.client else None)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=user.role,
        user_id=user.id,
    )


@router.post("/login", response_model=TokenResponse, summary="Email/password login for clinicians and admins")
@limiter.limit("10/minute")
async def email_login(body: EmailLogin, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is inactive")

    # TOTP check for clinicians
    if user.totp_enabled and user.role == UserRole.CLINICIAN:
        if not body.totp_code:
            raise HTTPException(
                status_code=status.HTTP_428_PRECONDITION_REQUIRED,
                detail="2FA code required",
                headers={"X-Requires-TOTP": "true"},
            )
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(body.totp_code, valid_window=1):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid 2FA code")

    access_token = create_access_token({"sub": user.id, "role": user.role.value})
    refresh_token = create_refresh_token({"sub": user.id})

    await log_event(db, "user_login", user_id=user.id, description=f"{user.role.value} email login",
                    ip_address=request.client.host if request.client else None)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=user.role,
        user_id=user.id,
    )


@router.post("/refresh", response_model=TokenResponse, summary="Refresh access token")
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_refresh_token(body.refresh_token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access_token = create_access_token({"sub": user.id, "role": user.role.value})
    new_refresh = create_refresh_token({"sub": user.id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        role=user.role,
        user_id=user.id,
    )


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/totp/setup", response_model=TOTPSetupResponse, summary="Set up 2FA for clinician")
async def setup_totp(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role not in (UserRole.CLINICIAN, UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only clinicians/admins can set up 2FA")

    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=current_user.email or str(current_user.id), issuer_name="TeleHealth")

    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    current_user.totp_secret = secret
    await db.commit()

    return TOTPSetupResponse(
        secret=secret,
        qr_code_url=f"data:image/png;base64,{qr_b64}",
        backup_codes=[pyotp.random_base32()[:8] for _ in range(8)],
    )


@router.post("/totp/enable", summary="Enable 2FA after setup verification")
async def enable_totp(
    body: TOTPVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TOTP not set up. Call /auth/totp/setup first.")

    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(body.totp_code, valid_window=1):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid TOTP code")

    current_user.totp_enabled = True
    await db.commit()
    return {"message": "2FA enabled successfully"}
