"""Accounts: a public handle, the address of the profile (U14), made for the accounts that exist.

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-29

The rule is ``app/accounts/handles.py``'s, repeated here because a migration never imports the application's code:
the display name's letters and digits, accents removed, lower case, joined by hyphens, a number added when taken.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _slug(name: str) -> str:
    plain = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode("ascii").lower()
    out = "-".join(re.findall(r"[a-z0-9]+", plain))[:60].strip("-")
    return out or "account"


def upgrade() -> None:
    with op.batch_alter_table("user") as batch:
        batch.add_column(sa.Column("handle", sa.String(length=64), nullable=True))
        batch.create_unique_constraint("uq_user_handle", ["handle"])
    conn = op.get_bind()
    taken: set[str] = set()
    for row in conn.execute(sa.text("SELECT id, display_name FROM user ORDER BY created_at, id")).all():
        base = _slug(row.display_name)
        handle, n = base, 2
        while handle in taken:
            handle, n = f"{base}-{n}", n + 1
        taken.add(handle)
        conn.execute(sa.text("UPDATE user SET handle = :h WHERE id = :i"), {"h": handle, "i": row.id})


def downgrade() -> None:
    with op.batch_alter_table("user") as batch:
        batch.drop_constraint("uq_user_handle", type_="unique")
        batch.drop_column("handle")
