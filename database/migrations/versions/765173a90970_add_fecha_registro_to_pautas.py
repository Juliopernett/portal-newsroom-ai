"""add fecha_registro to pautas

Revision ID: 765173a90970
Revises: 70cb814760e7
Create Date: 2026-08-04 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "765173a90970"
down_revision: str | Sequence[str] | None = "70cb814760e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default backfills existing rows with "now" (migration-run time) —
    # we have no true creation timestamp for pautas created before this
    # column existed, so this marks when audit tracking started.
    # batch_alter_table (not a plain op.add_column): SQLite rejects
    # ADD COLUMN ... NOT NULL DEFAULT CURRENT_TIMESTAMP in one step
    # (non-constant default), batch mode recreates the table instead —
    # works identically on Postgres, which has no such restriction.
    with op.batch_alter_table("pautas") as batch_op:
        batch_op.add_column(
            sa.Column(
                "fecha_registro",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            )
        )
    with op.batch_alter_table("pautas") as batch_op:
        batch_op.alter_column("fecha_registro", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("pautas", "fecha_registro")
