"""create identidad_comercial table

Revision ID: c4d6e8f0a2b4
Revises: b7c9e1f3a5d7
Create Date: 2026-08-19 00:00:00.000000

No seed row — the table starts empty and `GET /identidad-comercial`
returns 404 until an operator fills the Configuración form for the first
time (see `core.entities.identidad_comercial`).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d6e8f0a2b4"
down_revision: str | Sequence[str] | None = "b7c9e1f3a5d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "identidad_comercial",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("nombre_comercial", sa.String(), nullable=False),
        sa.Column("razon_social", sa.String(), nullable=True),
        sa.Column("nit", sa.String(length=50), nullable=True),
        sa.Column("telefono", sa.String(length=30), nullable=True),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("sitio_web", sa.String(length=200), nullable=True),
        sa.Column("instagram", sa.String(length=100), nullable=True),
        sa.Column("facebook", sa.String(length=200), nullable=True),
        sa.Column("otras_redes", sa.String(), nullable=True),
        sa.Column("logo_storage_key", sa.String(), nullable=True),
        sa.Column("logo_content_type", sa.String(length=100), nullable=True),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("identidad_comercial")
