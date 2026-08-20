"""Translates domain/persistence errors into HTTP responses.

Keeps route handlers free of try/except boilerplate. Without this, a
`ValueError` raised by an entity's own validation (`core/entities/`) or an
`IntegrityError` raised by a foreign key constraint would surface as an
opaque 500 instead of a response the caller can actually act on.
"""

from __future__ import annotations

import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from agents.meta_social.client import MetaGraphConfigurationError
from agents.wordpress.client import WordPressConfigurationError


def register_exception_handlers(app: FastAPI) -> None:
    """Register the handlers that turn domain/persistence errors into 4xx responses."""

    @app.exception_handler(ValueError)
    async def handle_value_error(_request: Request, exc: ValueError) -> JSONResponse:
        """A domain entity rejected its own data — see `core/entities/*.py`."""
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(_request: Request, _exc: IntegrityError) -> JSONResponse:
        """A foreign key (or other database constraint) was violated on commit."""
        return JSONResponse(
            status_code=400,
            content={"detail": "Referenced entity does not exist or violates a constraint"},
        )

    @app.exception_handler(WordPressConfigurationError)
    async def handle_wordpress_configuration_error(
        _request: Request, exc: WordPressConfigurationError
    ) -> JSONResponse:
        """WordPress credentials are not set in `.env` yet (Sprint 4A, Increment 3)."""
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(MetaGraphConfigurationError)
    async def handle_meta_graph_configuration_error(
        _request: Request, exc: MetaGraphConfigurationError
    ) -> JSONResponse:
        """Meta Graph API credentials are not set in `.env` yet (see agents.meta_social)."""
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(requests.RequestException)
    async def handle_external_request_error(
        _request: Request, exc: requests.RequestException
    ) -> JSONResponse:
        """An external HTTP integration (WordPress, Meta Graph API) rejected the
        request or was unreachable."""
        return JSONResponse(status_code=502, content={"detail": f"External request failed: {exc}"})
