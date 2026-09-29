"""Explore: a specimen's country (ISO 3166-1 alpha-2), stated by a source or implied by its coordinates; the text search
matches, and its FTS5 index kept in step by triggers.

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-29
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TRIGGERS = (
    "CREATE TRIGGER slide_search_insert AFTER INSERT ON slide BEGIN "
    "INSERT INTO slide_search(rowid, search_text) VALUES (new.id, new.search_text); END",
    "CREATE TRIGGER slide_search_delete AFTER DELETE ON slide BEGIN "
    "INSERT INTO slide_search(slide_search, rowid, search_text) VALUES ('delete', old.id, old.search_text); END",
    "CREATE TRIGGER slide_search_update AFTER UPDATE OF search_text ON slide BEGIN "
    "INSERT INTO slide_search(slide_search, rowid, search_text) VALUES ('delete', old.id, old.search_text); "
    "INSERT INTO slide_search(rowid, search_text) VALUES (new.id, new.search_text); END",
)


def upgrade() -> None:
    with op.batch_alter_table("slide") as batch:
        batch.add_column(sa.Column("country", sa.String(length=2), nullable=True))
        batch.add_column(sa.Column("search_text", sa.Text(), nullable=True))
        batch.create_index("ix_slide_country", ["country"])
    op.execute("CREATE VIRTUAL TABLE slide_search USING fts5(search_text, content='slide', content_rowid='id', "
               "tokenize='unicode61 remove_diacritics 2')")
    for trigger in TRIGGERS:
        op.execute(trigger)
    op.execute("INSERT INTO slide_search(slide_search) VALUES ('rebuild')")


def downgrade() -> None:
    for name in ("slide_search_insert", "slide_search_delete", "slide_search_update"):
        op.execute(f"DROP TRIGGER IF EXISTS {name}")
    op.execute("DROP TABLE IF EXISTS slide_search")
    with op.batch_alter_table("slide") as batch:
        batch.drop_index("ix_slide_country")
        batch.drop_column("search_text")
        batch.drop_column("country")
