"""news_candidates: stored cover, social text and WordPress publication tracking

Revision ID: f7c9e5a1b3d4
Revises: e6b8d4f0a2c3
Create Date: 2026-10-29 18:00:00.000000

Sprint "Procesadas": the cover's JPEG is kept in the app's storage
(`portada_storage_key`), the editorial AI also writes the Instagram/Facebook
text (`texto_redes`), and the last known WordPress state of the draft is
tracked (`wp_estado`, `wp_publicado_url`, `wp_fecha_publicacion`).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7c9e5a1b3d4"
down_revision: str | Sequence[str] | None = "e6b8d4f0a2c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("news_candidates") as batch_op:
        batch_op.add_column(sa.Column("portada_storage_key", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("texto_redes", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("wp_estado", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("wp_publicado_url", sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column("wp_fecha_publicacion", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("news_candidates") as batch_op:
        batch_op.drop_column("wp_fecha_publicacion")
        batch_op.drop_column("wp_publicado_url")
        batch_op.drop_column("wp_estado")
        batch_op.drop_column("texto_redes")
        batch_op.drop_column("portada_storage_key")
