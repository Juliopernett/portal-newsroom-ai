# Migrations

Alembic, inicializado en Sprint 3C (Commercial Core: `Client`, `Pauta`,
`PublicationRequest`). `env.py` no lee `sqlalchemy.url` de `alembic.ini`
— lo toma de `config.settings.get_settings().database_url` (`.env`),
igual que `database/engine.py`, para no duplicar configuración fuera de
`.env` (docs/PROJECT_RULES.md, regla 2).

## Comandos habituales

```bash
# Aplicar todas las migraciones pendientes (SQLite local o Postgres/Railway,
# según DATABASE_URL en .env)
alembic upgrade head

# Generar una migración nueva a partir de cambios en database/models/
alembic revision --autogenerate -m "descripción del cambio"

# Revertir todo (útil para probar que el esquema se reconstruye desde cero)
alembic downgrade base
```

## Convenciones

- Cada modelo ORM (`database/models/`) se registra automáticamente en
  `Base.metadata` al importar `database.models` — `env.py` ya lo hace, no
  hace falta listar modelos a mano.
- Los tipos `tipo`/`estado` (enums de dominio) se guardan como `String`
  simple, nunca como `ENUM` nativo de PostgreSQL — evita las migraciones
  costosas que implica alterar un tipo `ENUM` nativo cada vez que cambia
  un valor posible.
- Después de generar una migración con `--autogenerate`, revisarla a mano
  antes de aplicarla — Alembic detecta bien las tablas nuevas, pero no
  reemplaza criterio humano para índices, tipos ambiguos o renombrados.
