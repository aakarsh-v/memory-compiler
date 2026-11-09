"""Add events table for Phase 6

Revision ID: 003_add_events_table
Revises: 002_add_video_windows
Create Date: 2026-11-09 11:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003_add_events_table"
down_revision: Union[str, None] = "002_add_video_windows"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("video_id", sa.String(length=36), sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("start_seconds", sa.Float(), nullable=False, index=True),
        sa.Column("end_seconds", sa.Float(), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("action_label", sa.String(length=128), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("provenance_json", sa.JSON(), nullable=True),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("model_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_events_video_interval", "events", ["video_id", "start_seconds", "end_seconds"])


def downgrade() -> None:
    op.drop_table("events")
