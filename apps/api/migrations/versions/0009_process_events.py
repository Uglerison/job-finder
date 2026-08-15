"""Create interview, challenge and deadline events.

Revision ID: 0009_process_events
Revises: 0008_applications
Create Date: 2026-08-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_process_events"
down_revision: str | None = "0008_applications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "process_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timezone_name", sa.String(length=64), nullable=False, server_default="UTC"),
        sa.Column("participants", sa.JSON(), nullable=False),
        sa.Column("link", sa.String(length=2048), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="scheduled"),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
    )
    op.create_index("ix_process_events_application_id", "process_events", ["application_id"])


def downgrade() -> None:
    op.drop_index("ix_process_events_application_id", table_name="process_events")
    op.drop_table("process_events")
