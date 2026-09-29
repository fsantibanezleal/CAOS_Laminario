"""The community: identifications, votes, flags and moderation actions; the slide's community node and badge.

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-29

The first identification of each published slide (its contributor's, or its source's) is made by the idempotent
``python -m app.community backfill``, not here, so this migration never imports the application's code.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from fastapi_users_db_sqlalchemy.generics import GUID


revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("slide") as batch:
        batch.add_column(sa.Column("community_node", sa.String(length=200), nullable=True))
        batch.add_column(sa.Column("community_rank", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("badge", sa.String(length=12), nullable=True))
        batch.add_column(sa.Column("hidden_from", sa.String(length=16), nullable=True))
        batch.create_index("ix_slide_badge", ["badge"])
    with op.batch_alter_table("annotation") as batch:
        batch.add_column(sa.Column("hidden", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table(
        "identification",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(length=24), nullable=False, unique=True),
        sa.Column("slide_id", sa.Integer(), sa.ForeignKey("slide.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", GUID(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=True),
        sa.Column("anchor_kind", sa.String(length=12), nullable=False),
        sa.Column("anchor_ref", sa.String(length=200), nullable=False),
        sa.Column("anchor_name", sa.String(length=200), nullable=False),
        sa.Column("anchor_rank", sa.String(length=32), nullable=True),
        sa.Column("anchor_classification", sa.String(length=16), nullable=True),
        sa.Column("lineage_json", sa.Text(), nullable=False),
        sa.Column("previous_lineage_json", sa.Text(), nullable=True),
        sa.Column("disagreement", sa.Boolean(), nullable=True),
        sa.Column("body", sa.String(length=1000), nullable=True),
        sa.Column("current", sa.Boolean(), nullable=False),
        sa.Column("hidden", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_identification_slide_id", "identification", ["slide_id"])
    op.create_index("ix_identification_user_id", "identification", ["user_id"])
    op.create_table(
        "slide_vote",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("slide_id", sa.Integer(), sa.ForeignKey("slide.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", GUID(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("as_good_as_it_can_be", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("slide_id", "user_id"),
    )
    op.create_table(
        "flag",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(length=24), nullable=False, unique=True),
        sa.Column("target_kind", sa.String(length=16), nullable=False),
        sa.Column("target_id", sa.String(length=32), nullable=False),
        sa.Column("slide_id", sa.Integer(), sa.ForeignKey("slide.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", GUID(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(length=16), nullable=False),
        sa.Column("comment", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_by_id", GUID(), sa.ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolution", sa.String(length=1000), nullable=True),
    )
    op.create_index("ix_flag_slide_id", "flag", ["slide_id"])
    op.create_index("ix_flag_resolved_at", "flag", ["resolved_at"])
    op.create_table(
        "moderation_action",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("actor_id", GUID(), sa.ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=8), nullable=False),
        sa.Column("target_kind", sa.String(length=16), nullable=False),
        sa.Column("target_id", sa.String(length=32), nullable=False),
        sa.Column("slide_id", sa.Integer(), sa.ForeignKey("slide.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reason", sa.String(length=2000), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_moderation_action_target_kind_target_id", "moderation_action", ["target_kind", "target_id"])


def downgrade() -> None:
    op.drop_index("ix_moderation_action_target_kind_target_id", table_name="moderation_action")
    op.drop_table("moderation_action")
    op.drop_index("ix_flag_resolved_at", table_name="flag")
    op.drop_index("ix_flag_slide_id", table_name="flag")
    op.drop_table("flag")
    op.drop_table("slide_vote")
    op.drop_index("ix_identification_user_id", table_name="identification")
    op.drop_index("ix_identification_slide_id", table_name="identification")
    op.drop_table("identification")
    with op.batch_alter_table("annotation") as batch:
        batch.drop_column("hidden")
    with op.batch_alter_table("slide") as batch:
        batch.drop_index("ix_slide_badge")
        batch.drop_column("hidden_from")
        batch.drop_column("badge")
        batch.drop_column("community_rank")
        batch.drop_column("community_node")
