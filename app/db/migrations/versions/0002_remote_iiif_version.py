"""The IIIF Image API version of a remote asset's service.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-29
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("asset") as batch:
        batch.add_column(sa.Column("remote_iiif_version", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("asset") as batch:
        batch.drop_column("remote_iiif_version")
