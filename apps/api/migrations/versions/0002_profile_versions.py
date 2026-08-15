"""Create the versioned profile persistence model.

Revision ID: 0002_profile_versions
Revises: 0001_initial_schema
Create Date: 2026-08-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_profile_versions"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create logical profiles and their immutable version history."""

    op.create_table(
        "profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_table(
        "profile_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("profiles.id"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("criteria", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("profile_id", "version_number"),
    )
    op.create_index("ix_profile_versions_profile_id", "profile_versions", ["profile_id"])


def downgrade() -> None:
    """Remove the profile domain tables in reverse dependency order."""

    op.drop_index("ix_profile_versions_profile_id", table_name="profile_versions")
    op.drop_table("profile_versions")
    op.drop_table("profiles")
