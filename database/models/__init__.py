"""ORM models.

Each model here is a SQLAlchemy table mapping for one domain entity in
`core/entities/` — never a subclass of it, never subclassed by it (see
each model's own docstring). Re-exported below so `database.migrations.env`
only needs one import to register every table on `Base.metadata`.
"""

from __future__ import annotations

from database.models.client import ClientModel
from database.models.destino_publicacion import DestinoPublicacionModel
from database.models.gasto import GastoModel
from database.models.identidad_comercial import IdentidadComercialModel
from database.models.media_asset import MediaAssetModel
from database.models.pauta import PautaModel
from database.models.plan_pauta import PlanPautaModel
from database.models.publication_request import PublicationRequestModel
from database.models.session import SessionModel
from database.models.user import UserModel

__all__ = [
    "ClientModel",
    "DestinoPublicacionModel",
    "GastoModel",
    "IdentidadComercialModel",
    "MediaAssetModel",
    "PautaModel",
    "PlanPautaModel",
    "PublicationRequestModel",
    "SessionModel",
    "UserModel",
]
