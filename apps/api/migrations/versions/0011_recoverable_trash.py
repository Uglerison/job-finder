"""Add recoverable soft-delete fields to jobs.

Revision ID: 0011_recoverable_trash
Revises: 0010_closure_reasons
Create Date: 2026-08-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_recoverable_trash"
down_revision: str | None = "0010_closure_reasons"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("purge_after", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_jobs_deleted_at", "jobs", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_jobs_deleted_at", table_name="jobs")
    op.drop_column("jobs", "purge_after")
    op.drop_column("jobs", "deleted_at")
