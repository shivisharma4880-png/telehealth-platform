"""voice consult sessions

Revision ID: 002
Revises: 001
Create Date: 2026-04-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Clean up from any partially-applied attempt that left an orphaned ENUM type.
    op.execute(sa.text("DROP TABLE IF EXISTS voice_consult_sessions CASCADE"))
    op.execute(sa.text("DROP TYPE IF EXISTS voiceconsultsessstatus CASCADE"))

    op.create_table(
        "voice_consult_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("patient_id", sa.String(36), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="in_progress"),
        sa.Column("messages", sa.JSON, nullable=False),
        sa.Column("final_result", sa.JSON, nullable=True),
        sa.Column("patient_turns_completed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_voice_consult_sessions_patient_id", "voice_consult_sessions", ["patient_id"])


def downgrade() -> None:
    op.drop_index("ix_voice_consult_sessions_patient_id", table_name="voice_consult_sessions")
    op.drop_table("voice_consult_sessions")
