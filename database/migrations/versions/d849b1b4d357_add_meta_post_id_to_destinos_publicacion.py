"""add meta_post_id to destinos_publicacion

Revision ID: d849b1b4d357
Revises: e4ab8d762d1e
Create Date: 2026-08-20 00:00:00.000000

Sprint — conciliación inteligente de publicaciones en Meta. Captures the
Meta Graph API post/media id behind a FACEBOOK/INSTAGRAM destino's
`url_publicacion`, once the operator "relaciona" it via the
posts-recientes picker — see `core.entities.destino_publicacion`. Nullable
and unindexed for uniqueness on purpose: every destino confirmed before
this migration (and any manually-typed link afterward) has no
meta_post_id at all, so there is nothing to backfill.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d849b1b4d357"
down_revision: str | Sequence[str] | None = "e4ab8d762d1e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "destinos_publicacion", sa.Column("meta_post_id", sa.String(), nullable=True)
    )
    op.create_index(
        op.f("ix_destinos_publicacion_meta_post_id"),
        "destinos_publicacion",
        ["meta_post_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_destinos_publicacion_meta_post_id"), table_name="destinos_publicacion"
    )
    op.drop_column("destinos_publicacion", "meta_post_id")
