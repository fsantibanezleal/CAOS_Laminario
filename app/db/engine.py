"""Engines for the one SQLite database, shared by the API (asynchronous) and the worker (synchronous).

Every new connection sets:

- ``journal_mode=WAL``: readers never block the writer, which lets the API serve while the worker writes;
- ``busy_timeout=5000``: a writer waits up to five seconds for the lock instead of failing at once;
- ``foreign_keys=ON``: SQLite does not enforce foreign keys unless asked, per connection.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings

DATABASE_FILE = "laminario.sqlite3"
PRAGMAS = ("PRAGMA journal_mode=WAL", "PRAGMA busy_timeout=5000", "PRAGMA foreign_keys=ON")


def database_path(settings: Settings) -> Path:
    return settings.data_root / DATABASE_FILE


def sync_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def async_url(path: Path) -> str:
    return f"sqlite+aiosqlite:///{path.as_posix()}"


def _set_pragmas(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    for pragma in PRAGMAS:
        cursor.execute(pragma)
    cursor.close()


def make_sync_engine(path: Path) -> Engine:
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(sync_url(path))
    event.listen(engine, "connect", _set_pragmas)
    return engine


def make_async_engine(path: Path) -> AsyncEngine:
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(async_url(path))
    event.listen(engine.sync_engine, "connect", _set_pragmas)
    return engine


def sync_sessions(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)


def async_sessions(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
