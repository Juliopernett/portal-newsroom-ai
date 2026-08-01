"""ORM models.

Each model here is a SQLAlchemy table mapping for one domain entity in
`core/entities/` — never a subclass of it, never subclassed by it (see
each model's own docstring). Re-exported below so `database.migrations.env`
only needs one import to register every table on `Base.metadata`.
"""

from __future__ import annotations

from database.models.client import ClientModel
from database.models.pauta import PautaModel
from database.models.publication_request import PublicationRequestModel

__all__ = [
    "ClientModel",
    "PautaModel",
    "PublicationRequestModel",
]
