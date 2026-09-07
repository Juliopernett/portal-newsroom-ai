"""add source resolution fields to news_candidates

Revision ID: 7f3a1c9e2b5d
Revises: 180770bf0fc3
Create Date: 2026-08-29 00:00:00.000000

Sprint Discovery 3 — resolving the Google News discovery URL to the real
source and extracting its content. `server_default="pendiente"` on
`estado_resolucion` for the same reason `180770bf0fc3` used one on
`estado`: a `NOT NULL` column must not fail on any row already in
`news_candidates`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7f3a1c9e2b5d"
down_revision: str | Sequence[str] | None = "180770bf0fc3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("news_candidates", sa.Column("url_fuente_original", sa.String(), nullable=True))
    op.add_column(
        "news_candidates",
        sa.Column(
            "estado_resolucion", sa.String(length=20), nullable=False, server_default="pendiente"
        ),
    )
    op.add_column(
        "news_candidates", sa.Column("extracted_content_json", sa.String(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("news_candidates", "extracted_content_json")
    op.drop_column("news_candidates", "estado_resolucion")
    op.drop_column("news_candidates", "url_fuente_original")
