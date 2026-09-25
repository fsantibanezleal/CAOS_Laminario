"""The single declarative base every table uses, with a naming convention.

A fixed naming convention gives every index and constraint a stable name, which SQLite migrations need
(Alembic rebuilds tables in batch mode and refers to constraints by name).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def utcnow() -> datetime:
    """Timezone-aware UTC now; stored as naive UTC by SQLite."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
