"""FastAPI application for the internal Commercial Core API (Sprint 3D).

Run locally with:

    uvicorn app.api.main:app --reload

Then open http://127.0.0.1:8000/ — the React frontend (`frontend/`,
built to `frontend/dist/` at Docker build time) is served from the same
app so it never needs CORS. No custom OpenAPI — FastAPI's default
`/docs` is enough for a first internal interface, per this sprint's
explicit scope.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response

from app.api.errors import register_exception_handlers
from app.api.routers import (
    auth,
    clients,
    dashboard,
    gastos,
    insights,
    pautas,
    publication_requests,
    reportes,
)

FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"
FRONTEND_INDEX = FRONTEND_DIST / "index.html"

app = FastAPI(title="Portal Newsroom AI — Commercial Core API")

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(dashboard.router)
app.include_router(gastos.router)
app.include_router(insights.router)
app.include_router(pautas.router)
app.include_router(publication_requests.router)
app.include_router(reportes.router)

# Some React Router client routes share their exact top-level path with an
# API router prefix (`/gastos`, `/reportes`) — the same collision the dev
# Vite proxy resolves in `frontend/vite.config.ts::backendProxy()`. There's
# only one origin in production, so this middleware does the equivalent
# job: a real static file on disk always wins (JS/CSS bundle, favicon...);
# otherwise, a real browser navigation (`Accept: text/html`) gets the SPA
# shell so React Router can take over — UNLESS the path is one that must
# always reach a router (a CSV download, a media file stream: both opened
# via `target="_blank"`, which is *also* a full-page `text/html` request,
# so Accept alone can't tell them apart from a page visit).
_ALWAYS_BACKEND_PREFIXES = ("/publication-requests", "/docs", "/redoc", "/openapi.json")
_HAS_FILE_EXTENSION = re.compile(r"\.[A-Za-z0-9]{2,5}$")


@app.middleware("http")
async def serve_frontend(request: Request, call_next) -> Response:
    if request.method != "GET" or not FRONTEND_INDEX.exists():
        return await call_next(request)

    path = request.url.path
    if path.startswith(_ALWAYS_BACKEND_PREFIXES):
        return await call_next(request)

    if path != "/":
        candidate = (FRONTEND_DIST / path.lstrip("/")).resolve()
        if candidate.is_file() and candidate.is_relative_to(FRONTEND_DIST.resolve()):
            return FileResponse(candidate)

    accept = request.headers.get("accept", "")
    if "text/html" in accept and not _HAS_FILE_EXTENSION.search(path):
        return FileResponse(FRONTEND_INDEX)

    return await call_next(request)
