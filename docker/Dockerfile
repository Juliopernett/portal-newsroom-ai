# Builds the React frontend (frontend/dist) separately so the final image
# never needs Node installed — only the static build output is copied in.
FROM node:24-slim AS frontend-build

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build

FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# requirements.txt is the human-edited source (version ranges) pip-compile
# reads; requirements.lock.txt is what actually gets installed — every
# version pinned exactly, regenerated with `pip-compile requirements.txt
# -o requirements.lock.txt` whenever requirements.txt changes, so a given
# build is reproducible/auditable instead of resolving afresh each time
# (security audit 2026-08-20, L3). No `--generate-hashes`/`--require-hashes`
# here: this file is generated on a Python 3.14 host, this image runs
# 3.13 — a hash pins the exact wheel file, which can differ by
# interpreter/ABI, so enforcing hashes here could break a build over a
# wheel mismatch that isn't actually a supply-chain problem.
COPY requirements.txt requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt

COPY . .
COPY --from=frontend-build /frontend/dist ./frontend/dist

# Migrates the database, then starts the API/UI (`app/api/main.py` serves
# the React build from `frontend/dist/`, copied in above). Shell form (not
# exec-form JSON array) so $PORT — which Railway injects at runtime, and
# which varies per deploy — actually gets expanded; it defaults to 8000 for
# local `docker compose up`, where nothing sets $PORT. `python -m` for
# both, not the bare `alembic`/`uvicorn` console scripts: whether they
# land on PATH depends on how pip installs them, `python -m` never does.
CMD ["sh", "-c", "python -m alembic upgrade head && python -m uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
