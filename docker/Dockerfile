FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Migrates the database, then starts the API/UI. Shell form (not exec-form
# JSON array) so $PORT — which Railway injects at runtime, and which
# varies per deploy — actually gets expanded; it defaults to 8000 for
# local `docker compose up`, where nothing sets $PORT. `python -m` for
# both, not the bare `alembic`/`uvicorn` console scripts: whether they
# land on PATH depends on how pip installs them, `python -m` never does.
CMD ["sh", "-c", "python -m alembic upgrade head && python -m uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
