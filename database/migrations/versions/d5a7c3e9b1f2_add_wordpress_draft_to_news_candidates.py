"""add wp_post_id / wp_url to news_candidates

Revision ID: d5a7c3e9b1f2
Revises: c4d8e2f6a1b3
Create Date: 2026-10-29 00:00:00.000000

Sprint Discovery 5: "Crear noticia" now rewrites the candidate with the
editorial AI and creates a WordPress draft; these two nullable columns
keep the link to that draft.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5a7c3e9b1f2"
down_revision: str | Sequence[str] | None = "c4d8e2f6a1b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("news_candidates") as batch_op:
        batch_op.add_column(sa.Column("wp_post_id", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("wp_url", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("news_candidates") as batch_op:
        batch_op.drop_column("wp_url")
        batch_op.drop_column("wp_post_id")
