"""Alembic environment.

The database URL is never read from `alembic.ini` — it comes from
`config.settings.get_settings()`, the single source of truth for
configuration (docs/PROJECT_RULES.md, rule 2), the same as
`database.engine.get_engine()`. Importing `database.models` registers
every ORM model on `Base.metadata` before `target_metadata` is read, so
autogenerate sees `ClientModel`, `PautaModel` and `PublicationRequestModel`
without listing them here by hand.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

import database.models  # noqa: F401  (import for its side effect: registers tables)
from config.settings import get_settings
from database.base import Base
from database.engine import normalize_database_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", normalize_database_url(get_settings().database_url))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection, emitting SQL to stdout."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live DB connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
