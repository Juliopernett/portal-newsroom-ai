"""create sources table, seed Google News, index news_candidates

Revision ID: a9e1c7d3f5b6
Revises: f7c9e5a1b3d4
Create Date: 2026-10-29 20:00:00.000000

Sprint Fuentes: Radar sources move from a hand-built object in a script to
a table the operator edits from the UI. The existing Google News source is
seeded with the SAME id the script always used (`radar-google-news-vallenato`)
because the dedup hash is computed from (source id, url) — a different id
would make every already-stored candidate look new again.

Also indexes `news_candidates.discovered_at`/`estado`, which the Radar list
and the scan now filter on.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a9e1c7d3f5b6"
down_revision: str | Sequence[str] | None = "f7c9e5a1b3d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_GOOGLE_NEWS_URL = "https://news.google.com/rss/search?q=vallenato&hl=es-419&gl=CO&ceid=CO:es-419"


def upgrade() -> None:
    sources = op.create_table(
        "sources",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("last_scan", sa.DateTime(timezone=True), nullable=True),
        sa.Column("intervalo_minutos", sa.Integer(), nullable=False),
        sa.Column("max_items", sa.Integer(), nullable=False),
        sa.Column("max_age_days", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.Column("errores_consecutivos", sa.Integer(), nullable=False),
        sa.Column("etag", sa.String(), nullable=True),
        sa.Column("last_modified", sa.String(), nullable=True),
        sa.Column("last_new_count", sa.Integer(), nullable=False),
    )
    op.bulk_insert(
        sources,
        [
            {
                "id": "radar-google-news-vallenato",
                "name": "Google Noticias — vallenato",
                "type": "rss",
                "url": _GOOGLE_NEWS_URL,
                "enabled": True,
                "priority": 0,
                "last_scan": None,
                "intervalo_minutos": 180,
                "max_items": 30,
                "max_age_days": 7,
                "last_error": None,
                "errores_consecutivos": 0,
                "etag": None,
                "last_modified": None,
                "last_new_count": 0,
            }
        ],
    )
    op.create_index("ix_news_candidates_discovered_at", "news_candidates", ["discovered_at"])
    op.create_index("ix_news_candidates_estado", "news_candidates", ["estado"])


def downgrade() -> None:
    op.drop_index("ix_news_candidates_estado", table_name="news_candidates")
    op.drop_index("ix_news_candidates_discovered_at", table_name="news_candidates")
    op.drop_table("sources")
