"""Initial schema for videos, processing_jobs, and frames

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-09 10:13:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "videos",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("owner_id", sa.String(length=128), nullable=False, index=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False, unique=True),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("fps", sa.Float(), nullable=True),
        sa.Column("has_audio", sa.Boolean(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, default="UPLOADED", index=True),
        sa.Column("current_stage", sa.String(length=64), nullable=True),
        sa.Column("progress", sa.Float(), nullable=False, default=0.0),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_videos_owner_status", "videos", ["owner_id", "status"])

    op.create_table(
        "processing_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("video_id", sa.String(length=36), sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("status", sa.String(length=32), nullable=False, default="QUEUED", index=True),
        sa.Column("attempt", sa.Integer(), nullable=False, default=1),
        sa.Column("stage", sa.String(length=64), nullable=True),
        sa.Column("progress", sa.Float(), nullable=False, default=0.0),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "frames",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("video_id", sa.String(length=36), sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("scene_id", sa.String(length=36), nullable=True),
        sa.Column("timestamp_seconds", sa.Float(), nullable=False, index=True),
        sa.Column("image_key", sa.String(length=512), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("embedding_model", sa.String(length=128), nullable=False),
        sa.Column("preprocessing_version", sa.String(length=64), nullable=False, default="v1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("video_id", "timestamp_seconds", "preprocessing_version", name="uq_frame_video_ts_version"),
    )
    op.create_index("idx_frames_video_timestamp", "frames", ["video_id", "timestamp_seconds"])


def downgrade() -> None:
    op.drop_table("frames")
    op.drop_table("processing_jobs")
    op.drop_table("videos")

