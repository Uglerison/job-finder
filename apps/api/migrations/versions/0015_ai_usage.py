"""Store usage metadata for each immutable AI analysis."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_ai_usage"
down_revision: str | None = "0014_job_analysis_versions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "job_analysis_versions",
        sa.Column("usage", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )


def downgrade() -> None:
    op.drop_column("job_analysis_versions", "usage")
