"""Create default availability when the DB has no slots for a requested window."""
from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.practitioner import Practitioner
from app.models.slot import Slot, SlotStatus


def parse_slot_boundary(value: str) -> datetime:
    """Parse query param to UTC-aware datetime (timestamptz-safe)."""
    v = value.strip()
    if v.endswith("Z"):
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    dt = datetime.fromisoformat(v)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def ensure_slots_in_utc_window(
    db: AsyncSession,
    practitioner: Practitioner,
    window_from: datetime,
    window_to: datetime,
) -> None:
    """Insert AVAILABLE slots on a simple clinic grid if none exist in the window.

    Grid: Mon–Sat, 09:00–17:00 UTC, stepped by the practitioner's slot_duration_minutes.
    Skips times at or before now() so booking rules stay valid.
    """
    now = datetime.now(timezone.utc)
    if window_to <= window_from:
        return

    start_d = window_from.astimezone(timezone.utc).date()
    # window_to is exclusive upper bound (e.g. next calendar day 00:00 UTC)
    last_moment = window_to - timedelta(microseconds=1)
    end_d = last_moment.astimezone(timezone.utc).date()

    duration = max(5, int(practitioner.slot_duration_minutes or 15))
    day_cursor = start_d
    while day_cursor <= end_d:
        if day_cursor.weekday() == 6:  # Sunday
            day_cursor += timedelta(days=1)
            continue

        day_start = datetime.combine(day_cursor, time(9, 0), tzinfo=timezone.utc)
        day_end = datetime.combine(day_cursor, time(17, 0), tzinfo=timezone.utc)
        t = day_start
        while t + timedelta(minutes=duration) <= day_end:
            if t < window_from or t >= window_to:
                t += timedelta(minutes=duration)
                continue
            if t <= now:
                t += timedelta(minutes=duration)
                continue

            exists = await db.execute(
                select(Slot.id).where(
                    Slot.practitioner_id == practitioner.id,
                    Slot.start_time == t,
                )
            )
            if exists.scalar_one_or_none() is None:
                db.add(
                    Slot(
                        id=str(uuid.uuid4()),
                        practitioner_id=practitioner.id,
                        start_time=t,
                        end_time=t + timedelta(minutes=duration),
                        status=SlotStatus.AVAILABLE,
                    )
                )
            t += timedelta(minutes=duration)

        day_cursor += timedelta(days=1)
