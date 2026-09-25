"""Slides and assets: the slide case.

Revision ID: 0001
Revises:
Create Date: 2026-09-24
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "slide",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("short_id", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("origin", sa.String(length=16), nullable=False),
        sa.Column("format_code", sa.String(length=16), nullable=False),
        sa.Column("width_mm", sa.Float(), nullable=False),
        sa.Column("height_mm", sa.Float(), nullable=False),
        sa.Column("coverslip_code", sa.String(length=16), nullable=False),
        sa.Column("coverslip_long_mm", sa.Float(), nullable=True),
        sa.Column("coverslip_short_mm", sa.Float(), nullable=True),
        sa.Column("preparation", sa.String(length=24), nullable=False),
        sa.Column("stain", sa.String(length=80), nullable=True),
        sa.Column("mountant", sa.String(length=80), nullable=True),
        sa.Column("catalogue_number", sa.String(length=64), nullable=True),
        sa.Column("label_note", sa.String(length=160), nullable=True),
        sa.Column("prepared_on", sa.String(length=10), nullable=True),
        sa.Column("preparer", sa.String(length=120), nullable=True),
        sa.Column("anchor_kind", sa.String(length=12), nullable=False),
        sa.Column("anchor_ref", sa.String(length=200), nullable=False),
        sa.Column("anchor_name", sa.String(length=200), nullable=False),
        sa.Column("anchor_rank", sa.String(length=32), nullable=True),
        sa.Column("host_ref", sa.String(length=200), nullable=True),
        sa.Column("host_name", sa.String(length=200), nullable=True),
        sa.Column("host_rank", sa.String(length=32), nullable=True),
        sa.Column("type_status", sa.String(length=16), nullable=True),
        sa.Column("collected_on", sa.String(length=10), nullable=True),
        sa.Column("collector", sa.String(length=120), nullable=True),
        sa.Column("locality_text", sa.String(length=300), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column("uncertainty_m", sa.Float(), nullable=True),
        sa.Column("geoprivacy", sa.String(length=10), nullable=False),
        sa.Column("placement_node", sa.String(length=120), nullable=False),
        sa.Column("placement_override_reason", sa.String(length=300), nullable=True),
        sa.Column("contributor_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_slide")),
        sa.UniqueConstraint("short_id", name=op.f("uq_slide_short_id")),
    )
    with op.batch_alter_table("slide", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_slide_anchor_kind_anchor_ref"), ["anchor_kind", "anchor_ref"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_slide_placement_node"), ["placement_node"], unique=False)
        batch_op.create_index(batch_op.f("ix_slide_status"), ["status"], unique=False)

    op.create_table(
        "asset",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slide_id", sa.Integer(), nullable=False),
        sa.Column("family", sa.String(length=8), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("media_kind", sa.String(length=12), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("width_px", sa.Integer(), nullable=True),
        sa.Column("height_px", sa.Integer(), nullable=True),
        sa.Column("pixel_size_um", sa.Float(), nullable=True),
        sa.Column("modality", sa.String(length=16), nullable=True),
        sa.Column("stack", sa.String(length=64), nullable=True),
        sa.Column("plane_index", sa.Integer(), nullable=True),
        sa.Column("plane_depth_um", sa.Float(), nullable=True),
        sa.Column("polarisation_state", sa.String(length=4), nullable=True),
        sa.Column("polarisation_angle_deg", sa.Float(), nullable=True),
        sa.Column("caption", sa.String(length=300), nullable=True),
        sa.Column("licence_uri", sa.String(length=200), nullable=False),
        sa.Column("rights_holder", sa.String(length=200), nullable=True),
        sa.Column("creator", sa.String(length=200), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("source_record_id", sa.String(length=200), nullable=True),
        sa.Column("source_retrieved_on", sa.Date(), nullable=True),
        sa.Column("source_sha256", sa.String(length=64), nullable=True),
        sa.Column("storage_key", sa.String(length=300), nullable=True),
        sa.Column("bytes", sa.Integer(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("remote_info_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["slide_id"], ["slide.id"], name=op.f("fk_asset_slide_id_slide"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_asset")),
    )
    with op.batch_alter_table("asset", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_asset_slide_id"), ["slide_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("asset", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_asset_slide_id"))

    op.drop_table("asset")
    with op.batch_alter_table("slide", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_slide_status"))
        batch_op.drop_index(batch_op.f("ix_slide_placement_node"))
        batch_op.drop_index(batch_op.f("ix_slide_anchor_kind_anchor_ref"))

    op.drop_table("slide")
