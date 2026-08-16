"""Create editable job notes and reusable tags.

Revision ID: 0007_job_metadata
Revises: 0006_job_status
Create Date: 2026-08-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_job_metadata"
down_revision: str | None = "0006_job_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
    )
    op.create_index("ix_job_notes_job_id", "job_notes", ["job_id"])

    op.create_table(
        "job_tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False, unique=True),
    )
    op.create_table(
        "job_tag_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.ForeignKeyConstraint(["tag_id"], ["job_tags.id"]),
        sa.UniqueConstraint("job_id", "tag_id"),
    )
    op.create_index("ix_job_tag_links_job_id", "job_tag_links", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_job_tag_links_job_id", table_name="job_tag_links")
    op.drop_table("job_tag_links")
    op.drop_table("job_tags")
    op.drop_index("ix_job_notes_job_id", table_name="job_notes")
    op.drop_table("job_notes")
