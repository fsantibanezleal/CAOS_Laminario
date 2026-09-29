"""An account's public handle (U14, R-1401): the address of its profile, never its email.

The display name's letters and digits, accents removed, lower case, joined by hyphens, at most 60 characters
(``Ana Pérez`` is ``ana-perez``); a number is added when the handle is taken (``ana-perez-2``). An empty result (a
name of symbols only) becomes ``account``. Migration 0012 repeats this rule for the accounts made before it, since a
migration never imports the application's code.
"""

from __future__ import annotations

import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User

HANDLE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX = 60


def slug(name: str) -> str:
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii").lower()
    words = re.findall(r"[a-z0-9]+", plain)
    out = "-".join(words)[:MAX].strip("-")
    return out or "account"


async def free_handle(db: AsyncSession, name: str) -> str:
    base = slug(name)
    taken = set((await db.execute(select(User.handle).where(
        (User.handle == base) | User.handle.like(f"{base}-%")))).scalars())
    if base not in taken:
        return base
    n = 2
    while f"{base}-{n}" in taken:
        n += 1
    return f"{base}-{n}"
