import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    Column,
    String,
    Integer,
    BigInteger,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
    Index,
    JSON,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Video(Base):
    __tablename__ = "videos"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    owner_id = Column(String(128), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    storage_key = Column(String(512), unique=True, nullable=False)
    mime_type = Column(String(128), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)

    duration_seconds = Column(Float, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    fps = Column(Float, nullable=True)
    has_audio = Column(Boolean, nullable=True)

    status = Column(String(32), nullable=False, default="UPLOADED", index=True)
    current_stage = Column(String(64), nullable=True)
    progress = Column(Float, nullable=False, default=0.0)

    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    @property
    def video_id(self) -> str:
        return self.id

    # Relationships
    jobs = relationship("ProcessingJob", back_populates="video", cascade="all, delete-orphan", order_by="ProcessingJob.created_at.desc()")
    frames = relationship("Frame", back_populates="video", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_videos_owner_status", "owner_id", "status"),
    )


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    video_id = Column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="QUEUED", index=True)
    attempt = Column(Integer, nullable=False, default=1)
    stage = Column(String(64), nullable=True)
    progress = Column(Float, nullable=False, default=0.0)
    config_json = Column(JSON, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    error_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    video = relationship("Video", back_populates="jobs")


class Frame(Base):
    __tablename__ = "frames"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    video_id = Column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    scene_id = Column(String(36), nullable=True)
    timestamp_seconds = Column(Float, nullable=False, index=True)
    image_key = Column(String(512), nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)

    # Vector embedding stored as JSON for portable testing across SQLite / Postgres without extension requirement
    embedding = Column(JSON, nullable=True)
    embedding_model = Column(String(128), nullable=False)
    preprocessing_version = Column(String(64), nullable=False, default="v1")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    video = relationship("Video", back_populates="frames")

    __table_args__ = (
        UniqueConstraint("video_id", "timestamp_seconds", "preprocessing_version", name="uq_frame_video_ts_version"),
        Index("idx_frames_video_timestamp", "video_id", "timestamp_seconds"),
    )
