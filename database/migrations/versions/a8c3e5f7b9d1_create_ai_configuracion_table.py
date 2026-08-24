"""create ai_configuracion table

Revision ID: a8c3e5f7b9d1
Revises: f2a7c9e1b4d6
Create Date: 2026-08-24 00:00:00.000000

Sprint — configuración de proveedor de IA. A singleton table (one row,
always `core.entities.ai_configuracion.ID_UNICO`), same shape as
`identidad_comercial` — see that table's own creation migration
(c4d6e8f0a2b4). Starts empty: `app.api.dependencies.get_ai_provider`
falls back to Anthropic + Claude Opus 5 until an operator saves a row
from Configuración → IA.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a8c3e5f7b9d1"
down_revision: str | Sequence[str] | None = "f2a7c9e1b4d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "ai_configuracion",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("proveedor", sa.String(length=20), nullable=False),
        sa.Column("modelo", sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("ai_configuracion")
