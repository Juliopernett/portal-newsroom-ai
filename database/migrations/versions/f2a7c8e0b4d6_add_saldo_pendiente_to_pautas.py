"""add saldo_pendiente to pautas

Revision ID: f2a7c8e0b4d6
Revises: d4f8b6c9e1a3
Create Date: 2026-08-16 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2a7c8e0b4d6"
down_revision: str | Sequence[str] | None = "d4f8b6c9e1a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default backfills every existing pauta to "no debe nada" —
    # the correct assumption for every pauta recorded before this field
    # existed. batch_alter_table: SQLite rejects ADD COLUMN ... NOT NULL
    # DEFAULT in one step for a non-constant default in general, and this
    # keeps the same proven pattern 765173a90970 already used for
    # fecha_registro rather than a plain op.add_column.
    with op.batch_alter_table("pautas") as batch_op:
        batch_op.add_column(
            sa.Column(
                "saldo_pendiente",
                sa.Numeric(14, 2),
                nullable=False,
                server_default="0",
            )
        )
    with op.batch_alter_table("pautas") as batch_op:
        batch_op.alter_column("saldo_pendiente", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("pautas") as batch_op:
        batch_op.drop_column("saldo_pendiente")
