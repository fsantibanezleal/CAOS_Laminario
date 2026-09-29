"""A contribution's lifecycle: the case as sent, why it is back to draft, each image's token and failure.

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-29
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("slide") as batch:
        batch.add_column(sa.Column("status_reason", sa.String(length=300), nullable=True))
        batch.add_column(sa.Column("submission_json", sa.Text(), nullable=True))
    with op.batch_alter_table("asset") as batch:
        batch.add_column(sa.Column("client_token", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("failure", sa.String(length=300), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("asset") as batch:
        batch.drop_column("failure")
        batch.drop_column("client_token")
    with op.batch_alter_table("slide") as batch:
        batch.drop_column("submission_json")
        batch.drop_column("status_reason")
