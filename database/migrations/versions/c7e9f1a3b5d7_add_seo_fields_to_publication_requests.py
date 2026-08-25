"""add seo fields to publication_requests

Revision ID: c7e9f1a3b5d7
Revises: a8c3e5f7b9d1
Create Date: 2026-08-25 00:00:00.000000

Sprint — SEO real en la preparación editorial con IA. Adds
`meta_titulo_editorial`/`meta_descripcion_editorial`/`frase_clave_editorial`
to `publication_requests`, all nullable — feed Yoast SEO's own fields
(`_yoast_wpseo_title`/`_yoast_wpseo_metadesc`/`_yoast_wpseo_focuskw`,
confirmed REST-settable on the live WordPress site via `wp eval`,
2026-08-25) when creating a draft. Every solicitud that existed before
this migration keeps working unchanged.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7e9f1a3b5d7"
down_revision: str | Sequence[str] | None = "a8c3e5f7b9d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "publication_requests",
        sa.Column("meta_titulo_editorial", sa.String(length=70), nullable=True),
    )
    op.add_column(
        "publication_requests",
        sa.Column("meta_descripcion_editorial", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "publication_requests",
        sa.Column("frase_clave_editorial", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("publication_requests", "frase_clave_editorial")
    op.drop_column("publication_requests", "meta_descripcion_editorial")
    op.drop_column("publication_requests", "meta_titulo_editorial")
