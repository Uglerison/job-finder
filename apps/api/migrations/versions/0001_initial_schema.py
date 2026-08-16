"""Establish the first versioned schema for the local application database.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-15
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the Alembic version marker for the initial empty domain schema."""


def downgrade() -> None:
    """The initial marker has no domain tables to remove."""
