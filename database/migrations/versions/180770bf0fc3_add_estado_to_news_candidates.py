"""add estado to news_candidates

Revision ID: 180770bf0fc3
Revises: bd4bfd75a800
Create Date: 2026-08-26 00:00:00.000000

Sprint Discovery 2 — Radar Editorial. `server_default="nuevo"` so this
`NOT NULL` column doesn't fail on any row already in `news_candidates`
(none expected in production as of this migration, but defensive either
way — same convention as every other `*_estado` column in this project).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "180770bf0fc3"
down_revision: str | Sequence[str] | None = "bd4bfd75a800"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "news_candidates",
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="nuevo"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("news_candidates", "estado")
