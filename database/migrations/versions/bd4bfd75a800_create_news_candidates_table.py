"""create news_candidates table

Revision ID: bd4bfd75a800
Revises: c7e9f1a3b5d7
Create Date: 2026-08-25 15:51:21.854163

Sprint Discovery 1 — primera fuente real (RSS) conectada al
DiscoveryEngine. `hash` es unique — cinturón y tirantes junto al chequeo
`NewsCandidateRepository.exists(hash)` que ya hace
`core.services.radar_service.descubrir` antes de cada `save`, para que
una carrera (o un futuro caller que se salte ese chequeo) no pueda crear
dos filas para la misma noticia.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bd4bfd75a800"
down_revision: str | Sequence[str] | None = "c7e9f1a3b5d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "news_candidates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("summary", sa.String(), nullable=False),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hash", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", sa.String(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_news_candidates_source"), "news_candidates", ["source"], unique=False
    )
    op.create_index(
        op.f("ix_news_candidates_hash"), "news_candidates", ["hash"], unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_news_candidates_hash"), table_name="news_candidates")
    op.drop_index(op.f("ix_news_candidates_source"), table_name="news_candidates")
    op.drop_table("news_candidates")
