"""Add auditable reasons for closing applications.

Revision ID: 0010_closure_reasons
Revises: 0009_process_events
Create Date: 2026-08-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_closure_reasons"
down_revision: str | None = "0009_process_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("applications", sa.Column("closing_reason", sa.String(length=32), nullable=True))
    op.add_column("applications", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "application_events",
        sa.Column("closure_reason", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("application_events", "closure_reason")
    op.drop_column("applications", "closed_at")
    op.drop_column("applications", "closing_reason")
