"""Run the Alembic migrations programmatically (tests, local init, the deploy step).

The schema is created only by migrations, never by ``metadata.create_all``: what runs in production is what
the tests exercise.
"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from app.db.engine import make_sync_engine, sync_url
from app.version import ROOT


def alembic_config(database: Path) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "app" / "db" / "migrations"))
    config.set_main_option("sqlalchemy.url", sync_url(database))
    return config


def upgrade_to_head(database: Path) -> None:
    """Create or upgrade the database at ``database`` to the latest migration."""
    engine = make_sync_engine(database)  # creates the parent folder and sets the pragmas once
    engine.dispose()
    command.upgrade(alembic_config(database), "head")


if __name__ == "__main__":
    from app.config import get_settings
    from app.db.engine import database_path

    target = database_path(get_settings())
    upgrade_to_head(target)
    print(f"database at head: {target}")
