"""Uploads: one file sent through tusd for one asset of a contributor's draft.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-29
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "upload",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tus_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.CHAR(length=36), nullable=False),
        sa.Column("slide_id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("declared_type", sa.String(length=100), nullable=True),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("wsi", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("sniffed", sa.String(length=40), nullable=True),
        sa.Column("reason", sa.String(length=300), nullable=True),
        sa.Column("source_path", sa.String(length=500), nullable=True),
        sa.Column("job_id", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_upload_user_id_user"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["slide_id"], ["slide.id"], name=op.f("fk_upload_slide_id_slide"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asset_id"], ["asset.id"], name=op.f("fk_upload_asset_id_asset"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_upload")),
        sa.UniqueConstraint("tus_id", name=op.f("uq_upload_tus_id")),
    )
    op.create_index(op.f("ix_upload_user_id_status"), "upload", ["user_id", "status"], unique=False)
    op.create_index(op.f("ix_upload_asset_id"), "upload", ["asset_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_upload_asset_id"), table_name="upload")
    op.drop_index(op.f("ix_upload_user_id_status"), table_name="upload")
    op.drop_table("upload")
