"""Annotations: W3C Web Annotations on the assets of a slide, each by one account.

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-29
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from fastapi_users_db_sqlalchemy.generics import GUID


revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "annotation",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(length=24), nullable=False, unique=True),
        sa.Column("slide_id", sa.Integer(), sa.ForeignKey("slide.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("asset.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", GUID(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("body_json", sa.Text(), nullable=False),
        sa.Column("selector_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_annotation_asset_id", "annotation", ["asset_id"])


def downgrade() -> None:
    op.drop_index("ix_annotation_asset_id", table_name="annotation")
    op.drop_table("annotation")
