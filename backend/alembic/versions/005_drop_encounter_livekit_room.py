"""Remove LiveKit room name from encounters.

Revision ID: 005
Revises: 004
Create Date: 2026-05-04

"""
from typing import Sequence, Union

from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("encounters", "livekit_room_name")


def downgrade() -> None:
    import sqlalchemy as sa

    op.add_column(
        "encounters",
        sa.Column("livekit_room_name", sa.String(100), nullable=True, unique=True),
    )
