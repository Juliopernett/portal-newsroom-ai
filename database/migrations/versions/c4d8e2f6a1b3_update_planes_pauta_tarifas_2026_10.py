"""update planes_pauta to the 2026-10 tariffs (Normal/Oro)

Revision ID: c4d8e2f6a1b3
Revises: 7f3a1c9e2b5d
Create Date: 2026-10-28 00:00:00.000000

New brochure tariffs: 2 and 3 single publications and the 6-month / 1-year
Normal packages go up, the 2-month package is retired (`PlanPauta` has no
"activo" flag, so retiring means deleting — safe because `Pauta` has no FK
to this table) and four Oro packages are added (+35% over Normal, rounded
to $5.000). Included publications follow the tier: Normal 8/month, Oro
12/month. Plans are matched by their seeded ids from b7c9e1f3a5d7.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d8e2f6a1b3"
down_revision: str | Sequence[str] | None = "7f3a1c9e2b5d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PLAN_2_MESES = "b83046d6-e6a3-4f92-9973-f3368ceccb74"

# (id, nombre, cantidad, valor, dias, orden) — existing plans, new values.
_UPDATED = [
    ("8470de90-456c-45e4-9e55-df5fb5427216", "1 publicación", 1, "100000", 1, 0),
    ("e35e915a-18ae-47f4-ab9a-3f927b0859f4", "2 publicaciones", 2, "160000", 1, 1),
    ("aad0dc20-6a08-435b-b89a-df3f20812237", "3 publicaciones", 3, "220000", 1, 2),
    ("593cfb07-a8f2-44d7-9ae2-b1f97bbe7f1d", "1 mes Normal", 8, "430000", 30, 3),
    ("f4ea8de8-5cf8-41fc-a8a7-02b0532dae0c", "3 meses Normal", 24, "1100000", 90, 4),
    ("dfb3125f-4287-480d-8c4d-a4c6180a0ebf", "6 meses Normal", 48, "2000000", 180, 5),
    ("0b50436f-1258-412b-86e7-ff56de699839", "1 año Normal", 96, "3600000", 365, 6),
]

_ORO = [
    ("6a1f0c52-3d7e-4b19-8c24-5e9b7d0a1f31", "1 mes Oro", 12, "580000", 30, 7),
    ("9c2e4b78-1a5d-4f63-b0e7-2d8a6c3f5b42", "3 meses Oro", 36, "1485000", 90, 8),
    ("e7b35a91-6c4f-4d28-9a1b-8f0d2e6c4a53", "6 meses Oro", 72, "2700000", 180, 9),
    ("2d84f6c0-9b3a-4e75-a6d1-4c7e1b9f8a64", "1 año Oro", 144, "4860000", 365, 10),
]

# Previous values, only used by downgrade().
_PREVIOUS = [
    ("e35e915a-18ae-47f4-ab9a-3f927b0859f4", "2 publicaciones", 2, "150000", 1, 1),
    ("aad0dc20-6a08-435b-b89a-df3f20812237", "3 publicaciones", 3, "190000", 1, 2),
    ("593cfb07-a8f2-44d7-9ae2-b1f97bbe7f1d", "1 mes", 10, "430000", 30, 3),
    ("f4ea8de8-5cf8-41fc-a8a7-02b0532dae0c", "3 meses", 30, "1100000", 90, 5),
    ("dfb3125f-4287-480d-8c4d-a4c6180a0ebf", "6 meses", 60, "1780000", 180, 6),
    ("0b50436f-1258-412b-86e7-ff56de699839", "1 año", 120, "3050000", 365, 7),
]

_UPDATE = sa.text(
    "UPDATE planes_pauta SET nombre = :nombre, cantidad_publicaciones = :cantidad, "
    "valor = :valor, dias_vigencia = :dias, orden = :orden WHERE id = :id"
)
_INSERT = sa.text(
    "INSERT INTO planes_pauta (id, nombre, cantidad_publicaciones, valor, dias_vigencia, "
    "orden, fecha_registro) VALUES (:id, :nombre, :cantidad, :valor, :dias, :orden, "
    "CURRENT_TIMESTAMP)"
)


def _params(row: tuple) -> dict:
    id_, nombre, cantidad, valor, dias, orden = row
    return {
        "id": id_,
        "nombre": nombre,
        "cantidad": cantidad,
        "valor": valor,
        "dias": dias,
        "orden": orden,
    }


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    for row in _UPDATED:
        conn.execute(_UPDATE, _params(row))
    conn.execute(sa.text("DELETE FROM planes_pauta WHERE id = :id"), {"id": _PLAN_2_MESES})
    for row in _ORO:
        conn.execute(_INSERT, _params(row))


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    for row in _ORO:
        conn.execute(sa.text("DELETE FROM planes_pauta WHERE id = :id"), {"id": row[0]})
    for row in _PREVIOUS:
        conn.execute(_UPDATE, _params(row))
    conn.execute(
        sa.text("UPDATE planes_pauta SET nombre = '1 publicación', orden = 0 WHERE id = :id"),
        {"id": "8470de90-456c-45e4-9e55-df5fb5427216"},
    )
    conn.execute(_INSERT, _params((_PLAN_2_MESES, "2 meses", 20, "760000", 60, 4)))
