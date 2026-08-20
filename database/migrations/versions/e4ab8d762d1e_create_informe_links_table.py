"""create informe_links table

Revision ID: e4ab8d762d1e
Revises: c4d6e8f0a2b4
Create Date: 2026-08-19 00:00:00.000000

Backs the "Enviar por WhatsApp" share link on a Pauta's informe (Sprint —
enlace compartible del informe): a revocable-by-expiry token, same
discipline as `sessions` (see `core.entities.informe_link.InformeLink`),
not a signed/stateless one.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4ab8d762d1e"
down_revision: str | Sequence[str] | None = "c4d6e8f0a2b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "informe_links",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("pauta_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["pauta_id"], ["pautas.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_informe_links_pauta_id"), "informe_links", ["pauta_id"], unique=False
    )
    op.create_index(
        op.f("ix_informe_links_token_hash"), "informe_links", ["token_hash"], unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_informe_links_token_hash"), table_name="informe_links")
    op.drop_index(op.f("ix_informe_links_pauta_id"), table_name="informe_links")
    op.drop_table("informe_links")
