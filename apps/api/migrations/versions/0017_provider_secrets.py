"""Store encrypted credentials for external job providers."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_provider_secrets"
down_revision: str | None = "0016_saved_filters"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_secrets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider_key", sa.String(length=40), nullable=False),
        sa.Column("ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("salt", sa.LargeBinary(), nullable=False),
        sa.UniqueConstraint("provider_key"),
    )


def downgrade() -> None:
    op.drop_table("provider_secrets")
