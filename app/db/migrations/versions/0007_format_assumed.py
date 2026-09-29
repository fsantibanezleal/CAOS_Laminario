"""The base collection: a slide's format may be assumed when the source does not record it.

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-29
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("slide") as batch:
        batch.add_column(sa.Column("format_assumed", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table("slide") as batch:
        batch.drop_column("format_assumed")
