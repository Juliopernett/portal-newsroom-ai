"""add editorial ia fields to publication_requests

Revision ID: f2a7c9e1b4d6
Revises: d849b1b4d357
Create Date: 2026-08-21 00:00:00.000000

Sprint — preparación editorial con IA. Adds the AI-rewritten content
(`*_editorial`) plus a small status pair (`preparacion_ia_estado`/
`preparacion_ia_error`) to `publication_requests`, all nullable or
defaulted — every solicitud that existed before this migration keeps
working exactly as before, with `preparacion_ia_estado` simply defaulting
to `pendiente`. `texto` (the original, untouched) is not affected by this
migration at all — see `core.entities.publication_request`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2a7c9e1b4d6"
down_revision: str | Sequence[str] | None = "d849b1b4d357"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "publication_requests", sa.Column("contenido_editorial", sa.String(), nullable=True)
    )
    op.add_column(
        "publication_requests", sa.Column("entradilla_editorial", sa.String(), nullable=True)
    )
    op.add_column(
        "publication_requests", sa.Column("titulo_editorial", sa.String(), nullable=True)
    )
    op.add_column(
        "publication_requests", sa.Column("categoria_editorial", sa.String(), nullable=True)
    )
    op.add_column(
        "publication_requests", sa.Column("etiquetas_editorial", sa.String(), nullable=True)
    )
    op.add_column("publication_requests", sa.Column("slug_editorial", sa.String(), nullable=True))
    op.add_column(
        "publication_requests",
        sa.Column(
            "preparacion_ia_estado",
            sa.String(length=20),
            nullable=False,
            server_default="pendiente",
        ),
    )
    op.add_column(
        "publication_requests", sa.Column("preparacion_ia_error", sa.String(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("publication_requests", "preparacion_ia_error")
    op.drop_column("publication_requests", "preparacion_ia_estado")
    op.drop_column("publication_requests", "slug_editorial")
    op.drop_column("publication_requests", "etiquetas_editorial")
    op.drop_column("publication_requests", "categoria_editorial")
    op.drop_column("publication_requests", "titulo_editorial")
    op.drop_column("publication_requests", "entradilla_editorial")
    op.drop_column("publication_requests", "contenido_editorial")
