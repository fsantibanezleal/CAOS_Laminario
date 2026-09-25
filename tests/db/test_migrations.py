"""Migrations create exactly the schema the models declare, and every connection runs with the pragmas."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect, text

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.engine import make_sync_engine
from app.db.migrate import upgrade_to_head


def test_head_matches_models(tmp_path: Path):
    database = tmp_path / "head.sqlite3"
    upgrade_to_head(database)
    engine = make_sync_engine(database)
    inspector = inspect(engine)
    live_tables = set(inspector.get_table_names()) - {"alembic_version"}
    assert live_tables == set(Base.metadata.tables)
    for name, table in Base.metadata.tables.items():
        live_cols = {c["name"]: c for c in inspector.get_columns(name)}
        assert set(live_cols) == {c.name for c in table.columns}, name
        for column in table.columns:
            assert live_cols[column.name]["nullable"] == column.nullable, (name, column.name)
        live_indexes = {tuple(i["column_names"]) for i in inspector.get_indexes(name)}
        for index in table.indexes:
            assert tuple(c.name for c in index.columns) in live_indexes, (name, index.name)
    engine.dispose()


def test_upgrade_is_idempotent(tmp_path: Path):
    database = tmp_path / "twice.sqlite3"
    upgrade_to_head(database)
    upgrade_to_head(database)
    engine = make_sync_engine(database)
    with engine.connect() as conn:
        assert conn.execute(text("select version_num from alembic_version")).scalar_one() == "0001"
    engine.dispose()


def test_sqlite_pragmas_on_every_connection(tmp_path: Path):
    engine = make_sync_engine(tmp_path / "pragmas.sqlite3")
    for _ in range(2):
        with engine.connect() as conn:
            assert conn.execute(text("pragma journal_mode")).scalar_one().lower() == "wal"
            assert conn.execute(text("pragma busy_timeout")).scalar_one() == 5000
            assert conn.execute(text("pragma foreign_keys")).scalar_one() == 1
    engine.dispose()
