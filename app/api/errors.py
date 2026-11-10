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
from agents.youtube.client import YouTubeConfigurationError
from core.ports.youtube_reader import YouTubeError
from shared.logger import get_logger

logger = get_logger(__name__)


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

    @app.exception_handler(YouTubeConfigurationError)
    async def handle_youtube_configuration_error(
        _request: Request, exc: YouTubeConfigurationError
    ) -> JSONResponse:
        """`YOUTUBE_API_KEY` is not set yet (see agents.youtube)."""
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(YouTubeError)
    async def handle_youtube_error(_request: Request, exc: YouTubeError) -> JSONResponse:
        """A YouTube call failed (quota, rejected key, outage): safe, readable message."""
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.exception_handler(requests.RequestException)
    async def handle_external_request_error(
        _request: Request, exc: requests.RequestException
    ) -> JSONResponse:
        """An external HTTP integration (WordPress, Meta Graph API) rejected the
        request or was unreachable."""
        # Never echo `exc`: its text carries the full request URL, which for
        # the Meta Graph API includes `access_token` in the query string.
        logger.warning("External request failed: %s", type(exc).__name__)
        return JSONResponse(status_code=502, content={"detail": "External request failed"})
