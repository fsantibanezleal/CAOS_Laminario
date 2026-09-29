"""Accounts: users, their sessions, and the invitations that create them.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-29
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.CHAR(length=36), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=1024), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_superuser", sa.Boolean(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("role", sa.String(length=12), nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user")),
    )
    op.create_index(op.f("ix_user_email"), "user", ["email"], unique=True)
    op.create_table(
        "accesstoken",
        sa.Column("token", sa.String(length=43), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.CHAR(length=36), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=op.f("fk_accesstoken_user_id_user"), ondelete="cascade"),
        sa.PrimaryKeyConstraint("token", name=op.f("pk_accesstoken")),
    )
    op.create_index(op.f("ix_accesstoken_created_at"), "accesstoken", ["created_at"], unique=False)
    op.create_table(
        "invitation",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("token_sha256", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("role", sa.String(length=12), nullable=False),
        sa.Column("issued_by_id", sa.CHAR(length=36), nullable=True),
        sa.Column("note", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("used_by_id", sa.CHAR(length=36), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("mailed", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["issued_by_id"], ["user.id"], name=op.f("fk_invitation_issued_by_id_user"),
                                ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["used_by_id"], ["user.id"], name=op.f("fk_invitation_used_by_id_user"),
                                ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invitation")),
        sa.UniqueConstraint("token_sha256", name=op.f("uq_invitation_token_sha256")),
    )


def downgrade() -> None:
    op.drop_table("invitation")
    op.drop_index(op.f("ix_accesstoken_created_at"), table_name="accesstoken")
    op.drop_table("accesstoken")
    op.drop_index(op.f("ix_user_email"), table_name="user")
    op.drop_table("user")
