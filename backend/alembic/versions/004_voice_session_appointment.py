"""Optional appointment link on voice consult sessions.

Revision ID: 004
Revises: 003
Create Date: 2026-05-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "voice_consult_sessions",
        sa.Column("appointment_id", sa.String(36), nullable=True),
    )
    op.create_foreign_key(
        "fk_voice_consult_sessions_appointment_id",
        "voice_consult_sessions",
        "appointments",
        ["appointment_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_voice_consult_sessions_appointment_id",
        "voice_consult_sessions",
        ["appointment_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_voice_consult_sessions_appointment_id", table_name="voice_consult_sessions")
    op.drop_constraint(
        "fk_voice_consult_sessions_appointment_id",
        "voice_consult_sessions",
        type_="foreignkey",
    )
    op.drop_column("voice_consult_sessions", "appointment_id")
