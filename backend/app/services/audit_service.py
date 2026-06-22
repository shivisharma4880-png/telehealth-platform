from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditEvent
import uuid
from datetime import datetime, timezone


async def log_event(
    db: AsyncSession,
    event_type: str,
    user_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    description: str | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Log an audit event. Append-only — never update or delete."""
    event = AuditEvent(
        id=str(uuid.uuid4()),
        user_id=user_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        description=description,
        event_metadata=metadata,
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=datetime.now(timezone.utc),
    )
    db.add(event)
    # Flush but don't commit — let the caller control transaction
    await db.flush()
