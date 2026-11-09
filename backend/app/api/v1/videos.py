import shutil
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.config import settings
from app.core.auth import get_current_user_id
from app.core.errors import NotFoundException, ValidationException, PayloadTooLargeException
from app.db.session import get_db
from app.db.models import Video
from app.storage.local import LocalStorageService
from app.services.job_service import JobService
from app.schemas.video import (
    VideoUploadResponse,
    VideoStatusResponse,
    VideoResponse,
    VideoListResponse,
)

router = APIRouter(prefix="/api/v1/videos", tags=["videos"])


def get_storage_service() -> LocalStorageService:
    return LocalStorageService(settings.MEDIA_ROOT)


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=VideoUploadResponse)
def upload_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    storage: LocalStorageService = Depends(get_storage_service),
    owner_id: str = Depends(get_current_user_id)
) -> VideoUploadResponse:
    """
    Accepts multipart video upload, validates format and size, stores atomically,
    creates tracking records, and returns 202 Accepted promptly.
    """
    if not file.filename:
        raise ValidationException("VIDEO_INVALID_FILENAME", "Uploaded file must have a filename")

    job_service = JobService(db, storage)
    job_service.validate_upload(file.filename, file.content_type)

    # Read uploaded file content to compute size and persist
    file.file.seek(0, 2)
    size_bytes = file.file.tell()
    file.file.seek(0)

    if size_bytes > settings.max_upload_bytes:
        raise PayloadTooLargeException(
            "VIDEO_TOO_LARGE",
            f"File size ({size_bytes} bytes) exceeds limit of {settings.MAX_UPLOAD_MB} MB"
        )

    video = job_service.create_video_and_job(
        stream=file.file,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size_bytes,
        owner_id=owner_id
    )

    return VideoUploadResponse(
        video_id=video.id,
        status=video.status.lower(),
        status_url=f"/api/v1/videos/{video.id}/status"
    )


@router.get("", response_model=VideoListResponse)
def list_videos(
    cursor: Optional[str] = Query(None, description="Cursor for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Page limit"),
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_user_id)
) -> VideoListResponse:
    """List videos owned exclusively by the current user."""
    query = db.query(Video).filter(Video.owner_id == owner_id)

    if cursor:
        query = query.filter(Video.id < cursor)

    videos = query.order_by(desc(Video.id)).limit(limit + 1).all()

    next_cursor = None
    if len(videos) > limit:
        next_cursor = videos[limit].id
        videos = videos[:limit]

    return VideoListResponse(
        items=[VideoResponse.model_validate(v) for v in videos],
        cursor=next_cursor
    )


@router.get("/{video_id}", response_model=VideoResponse)
def get_video_detail(
    video_id: str,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_user_id)
) -> VideoResponse:
    """Retrieve video metadata owned by current user."""
    video = db.query(Video).filter(Video.id == video_id, Video.owner_id == owner_id).first()
    if not video:
        raise NotFoundException("VIDEO_NOT_FOUND", f"Video '{video_id}' not found")
    return VideoResponse.model_validate(video)


@router.get("/{video_id}/status", response_model=VideoStatusResponse)
def get_video_status(
    video_id: str,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_user_id)
) -> VideoStatusResponse:
    """Poll processing status, stage, honest progress, and safe error summary."""
    video = db.query(Video).filter(Video.id == video_id, Video.owner_id == owner_id).first()
    if not video:
        raise NotFoundException("VIDEO_NOT_FOUND", f"Video '{video_id}' not found")
    return VideoStatusResponse.from_video(video)
