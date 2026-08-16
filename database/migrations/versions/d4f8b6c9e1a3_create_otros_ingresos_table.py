"""create otros_ingresos table

Revision ID: d4f8b6c9e1a3
Revises: c1d9e3f4a7b2
Create Date: 2026-08-15 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4f8b6c9e1a3"
down_revision: str | Sequence[str] | None = "c1d9e3f4a7b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "otros_ingresos",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("origen", sa.String(), nullable=False),
        sa.Column("monto", sa.Numeric(14, 2), nullable=False),
        sa.Column("monto_usd", sa.Numeric(14, 2), nullable=True),
        sa.Column("fecha_cobro", sa.Date(), nullable=False),
        sa.Column("observaciones", sa.String(), nullable=True),
        sa.Column("fecha_registro", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_otros_ingresos_fecha_cobro"), "otros_ingresos", ["fecha_cobro"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_otros_ingresos_fecha_cobro"), table_name="otros_ingresos")
    op.drop_table("otros_ingresos")
