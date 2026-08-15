"""Add normalized publication and expiration dates to jobs.

Revision ID: 0005_job_dates
Revises: 0004_jobs
Create Date: 2026-08-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_job_dates"
down_revision: str | None = "0004_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store normalized publication and expiration timestamps."""

    op.add_column("jobs", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Remove normalized publication and expiration timestamps."""

    op.drop_column("jobs", "expires_at")
    op.drop_column("jobs", "published_at")
