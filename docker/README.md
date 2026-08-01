# Docker

`Dockerfile` construye la imagen de la aplicación (Python 3.13-slim +
dependencias de `requirements.txt`). Al arrancar el contenedor, aplica
las migraciones de Alembic (`alembic upgrade head`) y después inicia la
API/UI con uvicorn, escuchando en `$PORT` (Railway lo inyecta en
producción; `docker-compose.yml` lo deja en 8000 para desarrollo local).

`docker-compose.yml`, en la raíz del proyecto, define cómo se ejecuta esa
imagen localmente (variables de entorno vía `.env`, puerto 8000 publicado,
volúmenes para `logs/` y `database/`). No define un servicio `db`: la
misma imagen sirve tanto para SQLite (default local) como para PostgreSQL
— lo decide `DATABASE_URL` en `.env`, sin cambiar código (ver
`database/engine.py`, Sprint 3C). En producción, PostgreSQL vive en
Railway, no en este compose.

## Uso

```bash
docker compose up --build
```

Con `.env` copiado de `.env.example` (SQLite por default), la app queda
disponible en `http://localhost:8000/`.
