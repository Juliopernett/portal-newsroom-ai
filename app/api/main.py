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

from config.settings import get_settings
from app.api.errors import register_exception_handlers
from app.api.routers import (
    ai_configuracion,
    auth,
    chart,
    clients,
    dashboard,
    discovery,
    fuentes_radar,
    gastos,
    identidad_comercial,
    insights,
    otros_ingresos,
    pautas,
    plan_pauta,
    portadas,
    publication_requests,
    reportes,
    social,
)

FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"
FRONTEND_INDEX = FRONTEND_DIST / "index.html"

_IS_PRODUCTION = get_settings().environment == "production"

# Interactive API docs are an attack-surface map: off in production.
app = FastAPI(
    title="Portal Newsroom AI — Commercial Core API",
    docs_url=None if _IS_PRODUCTION else "/docs",
    redoc_url=None if _IS_PRODUCTION else "/redoc",
    openapi_url=None if _IS_PRODUCTION else "/openapi.json",
)

register_exception_handlers(app)

app.include_router(ai_configuracion.router)
app.include_router(auth.router)
app.include_router(chart.router)
app.include_router(chart.router_publico)
app.include_router(clients.router)
app.include_router(dashboard.router)
app.include_router(discovery.router)
app.include_router(fuentes_radar.router)
app.include_router(gastos.router)
app.include_router(identidad_comercial.router)
app.include_router(identidad_comercial.router_publico)
app.include_router(insights.router)
app.include_router(otros_ingresos.router)
app.include_router(pautas.router)
app.include_router(pautas.router_publico)
app.include_router(plan_pauta.router)
app.include_router(portadas.router)
app.include_router(publication_requests.router)
app.include_router(reportes.router)
app.include_router(social.router)

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
_ALWAYS_BACKEND_PREFIXES = (
    "/publication-requests",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/chart-vallenato/embed",
)
_HAS_FILE_EXTENSION = re.compile(r"\.[A-Za-z0-9]{2,5}$")

# Baseline security headers on every response (security audit 2026-08-20,
# finding M3): `nosniff` closes the MIME-sniffing angle a mislabeled
# upload could otherwise exploit (see H1/M2 — a closed content-type
# allow-list on every upload route, not this header alone, is the actual
# fix for those); `X-Frame-Options` blocks clickjacking (this app was
# never meant to be framed by anything); HSTS is safe to always send —
# Railway serves everything over HTTPS in production, and a browser
# ignores the header over plain HTTP dev anyway.
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}

# CSP for the React SPA: the bundle is same-origin (no inline scripts);
# styles allow 'unsafe-inline' because Tailwind/Radix/charts set style
# attributes; images allow https:/data:/blob: (news images, previews).
# Skipped for /docs, whose Swagger UI needs CDN assets (dev only).
_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob: https:; media-src 'self' blob:; font-src 'self' data:; "
    "connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; "
    "frame-ancestors 'none'"
)
_NO_CSP_PREFIXES = ("/docs", "/redoc", "/openapi.json")
# The only page meant to be framed by other websites (the Chart Vallenato
# card). It is server-rendered, has no script and sets its own CSP.
_EMBEBIBLE_PREFIX = "/chart-vallenato/embed"


@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    response = await call_next(request)
    response.headers.update(_SECURITY_HEADERS)
    if request.url.path.startswith(_EMBEBIBLE_PREFIX):
        # Framing is the whole point here; the route sets its own CSP
        # (no script, `frame-ancestors *`).
        del response.headers["X-Frame-Options"]
        response.headers.append("Vary", "Accept")
        return response
    # `/gastos` and `/reportes` are both a React page AND a JSON API on the
    # same URL, told apart only by `Accept`. Without `Vary: Accept` the
    # browser cache can answer the page's own data request with the cached
    # HTML shell (list showed "no hay gastos" while 48 existed).
    response.headers.append("Vary", "Accept")
    if not request.url.path.startswith(_NO_CSP_PREFIXES):
        response.headers["Content-Security-Policy"] = _CSP
    return response


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
        return FileResponse(FRONTEND_INDEX, headers={"Cache-Control": "no-cache"})

    return await call_next(request)
