"""The collection tree: the GBIF taxon cache, and the anchor classification, part and preservation of a slide.

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-29
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "taxon",
        sa.Column("key", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("rank", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("accepted_key", sa.Integer(), nullable=True),
        sa.Column("lineage_json", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_taxon")),
    )
    with op.batch_alter_table("slide") as batch:
        batch.add_column(sa.Column("anchor_classification", sa.String(length=16), nullable=True))
        batch.add_column(sa.Column("part", sa.String(length=40), nullable=True))
        batch.add_column(sa.Column("preservation", sa.String(length=10), nullable=False, server_default="recent"))


def downgrade() -> None:
    with op.batch_alter_table("slide") as batch:
        batch.drop_column("preservation")
        batch.drop_column("part")
        batch.drop_column("anchor_classification")
    op.drop_table("taxon")
