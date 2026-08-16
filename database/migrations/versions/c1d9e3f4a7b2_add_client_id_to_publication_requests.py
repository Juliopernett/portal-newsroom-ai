"""add client_id to publication_requests

Revision ID: c1d9e3f4a7b2
Revises: 4657d2234272
Create Date: 2026-08-15 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1d9e3f4a7b2"
down_revision: str | Sequence[str] | None = "4657d2234272"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # batch_alter_table: SQLite has no ALTER TABLE ADD CONSTRAINT — batch
    # mode recreates the table instead, same as 765173a90970's pattern.
    # Works identically on Postgres, which has no such restriction.
    with op.batch_alter_table("publication_requests") as batch_op:
        batch_op.add_column(sa.Column("client_id", sa.String(length=36), nullable=True))
        batch_op.create_index(
            op.f("ix_publication_requests_client_id"), ["client_id"], unique=False
        )
        batch_op.create_foreign_key(
            "fk_publication_requests_client_id_clients", "clients", ["client_id"], ["id"]
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("publication_requests") as batch_op:
        batch_op.drop_constraint(
            "fk_publication_requests_client_id_clients", type_="foreignkey"
        )
        batch_op.drop_index(op.f("ix_publication_requests_client_id"))
        batch_op.drop_column("client_id")
