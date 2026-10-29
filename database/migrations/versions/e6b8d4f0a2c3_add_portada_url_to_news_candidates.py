"""add portada_url to news_candidates

Revision ID: e6b8d4f0a2c3
Revises: d5a7c3e9b1f2
Create Date: 2026-10-29 12:00:00.000000

Sprint Portadas: "Crear noticia" can render the branded cover, upload it to
WordPress as the draft's featured image, and keep its public URL here so
the operator can download it for social networks.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e6b8d4f0a2c3"
down_revision: str | Sequence[str] | None = "d5a7c3e9b1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("news_candidates") as batch_op:
        batch_op.add_column(sa.Column("portada_url", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("news_candidates") as batch_op:
        batch_op.drop_column("portada_url")
