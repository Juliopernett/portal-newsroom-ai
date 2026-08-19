"""create planes_pauta table

Revision ID: b7c9e1f3a5d7
Revises: f2a7c8e0b4d6
Create Date: 2026-08-18 00:00:00.000000

Seeds the table with the catalog previously hardcoded as `PLANES_CATALOGO`
in `frontend/src/features/contratos/api.ts`, so the Plan shortcut in
PautaForm keeps offering the same options the moment this ships — the
catalog becomes editable in Configuración from here on, nothing changes
for existing `Pauta` rows (no FK to this table).
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c9e1f3a5d7"
down_revision: str | Sequence[str] | None = "f2a7c8e0b4d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SEED = [
    ("8470de90-456c-45e4-9e55-df5fb5427216", "1 publicación", 1, "100000", 1, 0),
    ("e35e915a-18ae-47f4-ab9a-3f927b0859f4", "2 publicaciones", 2, "150000", 1, 1),
    ("aad0dc20-6a08-435b-b89a-df3f20812237", "3 publicaciones", 3, "190000", 1, 2),
    ("593cfb07-a8f2-44d7-9ae2-b1f97bbe7f1d", "1 mes", 10, "430000", 30, 3),
    ("b83046d6-e6a3-4f92-9973-f3368ceccb74", "2 meses", 20, "760000", 60, 4),
    ("f4ea8de8-5cf8-41fc-a8a7-02b0532dae0c", "3 meses", 30, "1100000", 90, 5),
    ("dfb3125f-4287-480d-8c4d-a4c6180a0ebf", "6 meses", 60, "1780000", 180, 6),
    ("0b50436f-1258-412b-86e7-ff56de699839", "1 año", 120, "3050000", 365, 7),
]


def upgrade() -> None:
    """Upgrade schema."""
    planes_pauta = op.create_table(
        "planes_pauta",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("cantidad_publicaciones", sa.Integer(), nullable=False),
        sa.Column("valor", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("dias_vigencia", sa.Integer(), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("fecha_registro", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    ahora = datetime.now(UTC)
    op.bulk_insert(
        planes_pauta,
        [
            {
                "id": id_,
                "nombre": nombre,
                "cantidad_publicaciones": cantidad,
                "valor": valor,
                "dias_vigencia": dias,
                "orden": orden,
                "fecha_registro": ahora,
            }
            for id_, nombre, cantidad, valor, dias, orden in _SEED
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("planes_pauta")
