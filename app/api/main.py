"""FastAPI application for the internal Commercial Core API (Sprint 3D).

Run locally with:

    uvicorn app.api.main:app --reload

Then open http://127.0.0.1:8000/ — the Excel-replacement UI (Sprint
3D-UI) lives at `/ui/`, served as static files from the same app so it
never needs CORS. No custom OpenAPI — FastAPI's default `/docs` is enough
for a first internal interface, per this sprint's explicit scope.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.errors import register_exception_handlers
from app.api.routers import (
    auth,
    clients,
    dashboard,
    gastos,
    insights,
    pautas,
    publication_requests,
)

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Portal Newsroom AI — Commercial Core API")

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(dashboard.router)
app.include_router(gastos.router)
app.include_router(insights.router)
app.include_router(pautas.router)
app.include_router(publication_requests.router)

app.mount("/ui", StaticFiles(directory=STATIC_DIR, html=True), name="ui")


@app.get("/", include_in_schema=False)
def redirect_to_ui() -> RedirectResponse:
    """Send a bare visit to the app straight to the UI, not an empty JSON root."""
    return RedirectResponse(url="/ui/")
