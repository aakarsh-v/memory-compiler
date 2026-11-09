from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class VideoUploadResponse(BaseModel):
    video_id: str = Field(..., description="Unique UUID of the uploaded video")
    status: str = Field(..., description="Initial processing status, typically 'queued'")
    status_url: str = Field(..., description="Relative API URL to poll for processing status")


class VideoStatusResponse(BaseModel):
    video_id: str
    id: Optional[str] = None
    filename: Optional[str] = None
    status: str = Field(..., description="Current status: UPLOADED, QUEUED, PROBING, EXTRACTING_FRAMES, EMBEDDING_FRAMES, PERSISTING_INDEX, READY, FAILED")
    current_stage: Optional[str] = Field(None, description="Detailed stage currently executing")
    progress: float = Field(0.0, ge=0.0, le=1.0, description="Honest progress estimate between 0.0 and 1.0")
    error_code: Optional[str] = Field(None, description="Machine-readable error code if processing failed")
    error_message: Optional[str] = Field(None, description="Safe error message summary")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_video(cls, video) -> "VideoStatusResponse":
        return cls(
            video_id=video.id,
            id=video.id,
            filename=video.filename,
            status=video.status,
            current_stage=video.current_stage,
            progress=video.progress,
            error_code=video.error_code,
            error_message=video.error_message,
            created_at=video.created_at,
            updated_at=video.updated_at
        )


class VideoResponse(BaseModel):
    id: str
    owner_id: str
    filename: str
    mime_type: str
    size_bytes: int
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    has_audio: Optional[bool] = None
    status: str
    current_stage: Optional[str] = None
    progress: float
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VideoListResponse(BaseModel):
    items: List[VideoResponse]
    cursor: Optional[str] = Field(None, description="Cursor for fetching next page of results")
