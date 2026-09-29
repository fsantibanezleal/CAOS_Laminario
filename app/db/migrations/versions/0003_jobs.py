"""Jobs and their event journal (the worker's durable queue); what processing records on an asset.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-29
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("asset") as batch:
        batch.add_column(sa.Column("source_path", sa.String(length=500), nullable=True))
        batch.add_column(sa.Column("psnr_db", sa.Float(), nullable=True))
        batch.add_column(sa.Column("codec", sa.String(length=12), nullable=True))
    op.create_table(
        "job",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("heavy", sa.Boolean(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.Column("timeout_s", sa.Integer(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("slide_id", sa.Integer(), nullable=True),
        sa.Column("worker", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["slide_id"], ["slide.id"], name=op.f("fk_job_slide_id_slide"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job")),
        sa.UniqueConstraint("public_id", name=op.f("uq_job_public_id")),
    )
    op.create_index(op.f("ix_job_status_id"), "job", ["status", "id"], unique=False)
    op.create_index(op.f("ix_job_slide_id"), "job", ["slide_id"], unique=False)
    op.create_table(
        "job_event",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("event", sa.String(length=16), nullable=False),
        sa.Column("data_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["job.id"], name=op.f("fk_job_event_job_id_job"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_event")),
        sa.UniqueConstraint("job_id", "seq", name=op.f("uq_job_event_job_id")),
    )


def downgrade() -> None:
    op.drop_table("job_event")
    op.drop_index(op.f("ix_job_slide_id"), table_name="job")
    op.drop_index(op.f("ix_job_status_id"), table_name="job")
    op.drop_table("job")
    with op.batch_alter_table("asset") as batch:
        batch.drop_column("codec")
        batch.drop_column("psnr_db")
        batch.drop_column("source_path")
