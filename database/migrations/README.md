# Migrations

Vacío intencionalmente durante la fase Foundation.

Cuando se agregue el primer modelo ORM real (docs/ROADMAP.md, Fase 1), se
inicializará **Alembic** en esta carpeta (`alembic init database/migrations`)
para gestionar la evolución del esquema, tanto en SQLite (MVP) como en la
futura migración a PostgreSQL.

`alembic` ya está incluido en `requirements.txt` para no requerir un paso de
instalación adicional cuando llegue ese momento.
