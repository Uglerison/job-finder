"""Add the initial triage status to normalized jobs.

Revision ID: 0006_job_status
Revises: 0005_job_dates
Create Date: 2026-08-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_job_status"
down_revision: str | None = "0005_job_dates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store the initial manual-triage state for every job."""

    op.add_column(
        "jobs",
        sa.Column("status", sa.String(length=32), nullable=False, server_default="found"),
    )


def downgrade() -> None:
    """Remove the initial triage status column."""

    op.drop_column("jobs", "status")
