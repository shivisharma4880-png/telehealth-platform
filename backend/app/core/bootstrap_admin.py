"""
Built-in platform administrator — created/updated on every API startup.

Credentials are intentionally fixed in source so any deployment (local, Docker, GCP)
always has a known admin after the database is reachable. Replace or remove for
production if you do not want a shared password (prefer SSO or env-injected secrets).

Uses a syntactically valid email (EmailStr rejects addresses under the ``.local``
domain as reserved).
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

# RFC 5322 / Pydantic EmailStr–safe (``.local`` is rejected as a reserved special-use name).
PLATFORM_ADMIN_EMAIL = "platform-admin@telehealth.example.com"
_LEGACY_PLATFORM_ADMIN_EMAIL = "platform-admin@telehealth.local"

PLATFORM_ADMIN_PASSWORD = "TelehealthPlatformAdmin2026!"

PLATFORM_ADMIN_USER_ID = str(
    uuid.uuid5(uuid.NAMESPACE_DNS, "telehealth:platform-bootstrap-admin:v1")
)


async def ensure_platform_admin(db: AsyncSession) -> None:
    """Upsert the bootstrap admin: correct role, active, verified, password matches constant."""
    hp = hash_password(PLATFORM_ADMIN_PASSWORD)

    user = await db.get(User, PLATFORM_ADMIN_USER_ID)
    if user:
        user.email = PLATFORM_ADMIN_EMAIL
        user.hashed_password = hp
        user.role = UserRole.ADMIN
        user.is_active = True
        user.is_verified = True
        user.totp_enabled = False
        user.totp_secret = None
        logger.info("Updated platform bootstrap admin: %s", PLATFORM_ADMIN_EMAIL)
        return

    result = await db.execute(
        select(User).where(
            or_(
                User.email == PLATFORM_ADMIN_EMAIL,
                User.email == _LEGACY_PLATFORM_ADMIN_EMAIL,
            )
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.hashed_password = hp
        existing.role = UserRole.ADMIN
        existing.is_active = True
        existing.is_verified = True
        existing.totp_enabled = False
        existing.totp_secret = None
        existing.email = PLATFORM_ADMIN_EMAIL
        logger.info("Updated existing user as platform bootstrap admin: %s", PLATFORM_ADMIN_EMAIL)
        return

    db.add(
        User(
            id=PLATFORM_ADMIN_USER_ID,
            email=PLATFORM_ADMIN_EMAIL,
            hashed_password=hp,
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,
        )
    )
    logger.info("Created platform bootstrap admin: %s", PLATFORM_ADMIN_EMAIL)
