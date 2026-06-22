"""Allow prescriptions from AI voice consult (nullable encounter/practitioner).

Revision ID: 003
Revises: 002
Create Date: 2026-04-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "prescriptions",
        "encounter_id",
        existing_type=sa.String(36),
        nullable=True,
    )
    op.alter_column(
        "prescriptions",
        "practitioner_id",
        existing_type=sa.String(36),
        nullable=True,
    )
    op.add_column(
        "prescriptions",
        sa.Column("voice_consult_session_id", sa.String(36), nullable=True),
    )
    op.create_index(
        "ix_prescriptions_voice_consult_session_id",
        "prescriptions",
        ["voice_consult_session_id"],
    )
    op.create_foreign_key(
        "fk_prescriptions_voice_consult_session_id",
        "prescriptions",
        "voice_consult_sessions",
        ["voice_consult_session_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_prescriptions_voice_consult_session_id "
        "ON prescriptions (voice_consult_session_id) "
        "WHERE voice_consult_session_id IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_prescriptions_voice_consult_session_id")
    op.drop_constraint(
        "fk_prescriptions_voice_consult_session_id",
        "prescriptions",
        type_="foreignkey",
    )
    op.drop_index("ix_prescriptions_voice_consult_session_id", table_name="prescriptions")
    op.drop_column("prescriptions", "voice_consult_session_id")
    op.execute(
        "DELETE FROM medication_requests WHERE prescription_id IN "
        "(SELECT id FROM prescriptions WHERE encounter_id IS NULL OR practitioner_id IS NULL)"
    )
    op.execute(
        "DELETE FROM prescriptions WHERE encounter_id IS NULL OR practitioner_id IS NULL"
    )
    op.alter_column(
        "prescriptions",
        "practitioner_id",
        existing_type=sa.String(36),
        nullable=False,
    )
    op.alter_column(
        "prescriptions",
        "encounter_id",
        existing_type=sa.String(36),
        nullable=False,
    )
