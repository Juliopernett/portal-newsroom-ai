"""backfill PUBLICADA solicitudes to ACEPTADA + WORDPRESS destino

Revision ID: a1b2c3d4e5f6
Revises: 15f24c0ea8ef
Create Date: 2026-08-06 15:15:00.000000

Sprint 4A, Increment 4 (see docs/adr/ADR-006-multichannel-publication.md,
Decision 2/3): `PublicationRequestStatus.PUBLICADA` is retired —
`core.entities.publication_request.PublicationRequestStatus` no longer
has that member, so any row still storing `estado='publicada'` would
raise `ValueError` the moment `SqlAlchemyPublicationRequestRepository`
tries to read it back (`PublicationRequestStatus(model.estado)`).

Every `publicada` row today got there through the pre-Increment-3 single
implicit channel (WordPress, published by hand outside the system, then
marked "Publicar" here just to track quota) — see
`scripts/migrate_historical_data.py`, which populated the real
historical data this way. So each one is rewritten as: `estado`
`aceptada`, `fecha_cierre` set to `fecha_recepcion` (the closest known
timestamp — there was never a real "published at" field before this),
and one new `destinos_publicacion` row: `canal='wordpress'`,
`estado='publicado'`, `fecha_publicacion=fecha_recepcion`. This is
exactly the shape `core.services.publication_request_service.aceptar`
+ `core.services.destino_publicacion_service.marcar_publicado` produce
going forward (the "Publicar" button's compatibility flow), so
`esta_completa`/quota calculations give the identical answer after this
migration that `estado == PUBLICADA` gave before it.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "15f24c0ea8ef"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Rewrite every `estado='publicada'` PublicationRequest to `aceptada` +
    a compatibility WORDPRESS/publicado DestinoPublicacion."""
    conn = op.get_bind()
    solicitudes_publicadas = conn.execute(
        sa.text("SELECT id, fecha_recepcion FROM publication_requests WHERE estado = 'publicada'")
    ).fetchall()

    for solicitud_id, fecha_recepcion in solicitudes_publicadas:
        conn.execute(
            sa.text(
                """
                INSERT INTO destinos_publicacion
                    (id, publication_request_id, canal, estado, fecha_publicacion)
                VALUES
                    (:id, :publication_request_id, 'wordpress', 'publicado', :fecha_publicacion)
                """
            ),
            {
                "id": str(uuid4()),
                "publication_request_id": solicitud_id,
                "fecha_publicacion": fecha_recepcion,
            },
        )

    conn.execute(
        sa.text(
            """
            UPDATE publication_requests
            SET estado = 'aceptada', fecha_cierre = fecha_recepcion
            WHERE estado = 'publicada'
            """
        )
    )


def downgrade() -> None:
    """Best-effort reverse: only safe immediately after `upgrade()`, before any
    genuinely new WORDPRESS destino is created through the app. Identifies
    exactly the rows `upgrade()` touched (an `aceptada` solicitud whose only
    destino is a WORDPRESS/publicado one matching its own fecha_cierre) and
    reverts them."""
    conn = op.get_bind()
    candidatos = conn.execute(
        sa.text(
            """
            SELECT pr.id, d.id
            FROM publication_requests pr
            JOIN destinos_publicacion d ON d.publication_request_id = pr.id
            WHERE pr.estado = 'aceptada'
              AND pr.fecha_cierre IS NOT NULL
              AND pr.fecha_cierre = pr.fecha_recepcion
              AND d.canal = 'wordpress'
              AND d.estado = 'publicado'
              AND d.fecha_publicacion = pr.fecha_recepcion
              AND d.wp_post_id IS NULL
              AND d.wp_url IS NULL
              AND (
                  SELECT COUNT(*) FROM destinos_publicacion WHERE publication_request_id = pr.id
              ) = 1
            """
        )
    ).fetchall()

    for solicitud_id, destino_id in candidatos:
        conn.execute(sa.text("DELETE FROM destinos_publicacion WHERE id = :id"), {"id": destino_id})
        conn.execute(
            sa.text(
                "UPDATE publication_requests "
                "SET estado = 'publicada', fecha_cierre = NULL WHERE id = :id"
            ),
            {"id": solicitud_id},
        )
