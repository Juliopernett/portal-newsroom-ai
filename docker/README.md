# Docker

`Dockerfile` construye la imagen de la aplicación (Python 3.13-slim +
dependencias de `requirements.txt`).

`docker-compose.yml`, en la raíz del proyecto, define cómo se ejecuta esa
imagen (variables de entorno vía `.env`, volúmenes para `logs/` y
`database/`).

## Uso

```bash
docker compose up --build
```

Cuando el proyecto migre a PostgreSQL (docs/ROADMAP.md), se agregará un
servicio `db` en `docker-compose.yml`.
