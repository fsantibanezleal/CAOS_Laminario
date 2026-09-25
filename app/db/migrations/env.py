"""Alembic environment: migrations run against the models' metadata, in batch mode for SQLite."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import event, pool
from sqlalchemy import create_engine

from app.db import models  # noqa: F401  (registers the tables on the metadata)
from app.db.base import Base
from app.db.engine import _set_pragmas

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(config.get_main_option("sqlalchemy.url"), poolclass=pool.NullPool)
    event.listen(engine, "connect", _set_pragmas)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
