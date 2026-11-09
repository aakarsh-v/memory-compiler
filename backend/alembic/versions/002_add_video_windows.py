"""Add video_windows table for Phase 5

Revision ID: 002_add_video_windows
Revises: 001_initial_schema
Create Date: 2026-11-09 11:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002_add_video_windows"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "video_windows",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("video_id", sa.String(length=36), sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("start_seconds", sa.Float(), nullable=False, index=True),
        sa.Column("end_seconds", sa.Float(), nullable=False, index=True),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("model_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("video_id", "start_seconds", "end_seconds", "model_id", name="uq_window_video_interval_model"),
    )
    op.create_index("idx_windows_video_interval", "video_windows", ["video_id", "start_seconds", "end_seconds"])


def downgrade() -> None:
    op.drop_table("video_windows")

