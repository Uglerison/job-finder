"""Store encrypted local AI credentials.

Revision ID: 0013_ai_secrets
Revises: 0012_search_sources
Create Date: 2026-08-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_ai_secrets"
down_revision: str | None = "0012_search_sources"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the singleton ciphertext and salt record for the local AI vault."""

    op.create_table(
        "ai_secrets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("salt", sa.LargeBinary(), nullable=False),
    )


def downgrade() -> None:
    """Remove locally encrypted AI credentials."""

    op.drop_table("ai_secrets")
