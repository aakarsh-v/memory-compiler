import os
import re
import shutil
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Query, Header, Response, status
from fastapi.responses import StreamingResponse, FileResponse
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


@router.get("/{video_id}/stream")
def stream_video(
    video_id: str,
    range: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    storage: LocalStorageService = Depends(get_storage_service),
    owner_id: str = Depends(get_current_user_id)
) -> Response:
    """
    Streams private original media with HTTP Range (206 Partial Content) support,
    allowing direct player seeking to evidence timestamps.
    """
    video = db.query(Video).filter(Video.id == video_id, Video.owner_id == owner_id).first()
    if not video:
        raise NotFoundException("VIDEO_NOT_FOUND", f"Video '{video_id}' not found")

    file_path = storage.get_path(video.storage_key)
    file_size = os.path.getsize(file_path)

    if not range:
        return FileResponse(
            path=file_path,
            media_type=video.mime_type or "video/mp4",
            headers={"Accept-Ranges": "bytes"}
        )

    # Parse Range: bytes=start-end
    range_match = re.match(r"^bytes=(\d+)-(\d+)?$", range.strip())
    if not range_match:
        return Response(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            headers={"Content-Range": f"bytes */{file_size}"}
        )

    start = int(range_match.group(1))
    end = int(range_match.group(2)) if range_match.group(2) else file_size - 1

    if start >= file_size or end >= file_size or start > end:
        return Response(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            headers={"Content-Range": f"bytes */{file_size}"}
        )

    chunk_size = end - start + 1

    def iter_file():
        with open(file_path, "rb") as f:
            f.seek(start)
            remaining = chunk_size
            while remaining > 0:
                bytes_to_read = min(65536, remaining)
                data = f.read(bytes_to_read)
                if not data:
                    break
                remaining -= len(data)
                yield data

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_size),
        "Content-Type": video.mime_type or "video/mp4"
    }

    return StreamingResponse(
        iter_file(),
        status_code=status.HTTP_206_PARTIAL_CONTENT,
        headers=headers
    )


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(
    video_id: str,
    db: Session = Depends(get_db),
    storage: LocalStorageService = Depends(get_storage_service),
    owner_id: str = Depends(get_current_user_id)
) -> Response:
    """
    Deletes video, cascading to all jobs, frames, windows, events,
    and purging original media and frame thumbnails from storage without leaving orphans.
    """
    video = db.query(Video).filter(Video.id == video_id, Video.owner_id == owner_id).first()
    if not video:
        raise NotFoundException("VIDEO_NOT_FOUND", f"Video '{video_id}' not found or access denied")

    # Collect storage keys before deletion
    frame_keys = [f.image_key for f in video.frames]
    video_key = video.storage_key

    # Delete video row (cascades to all child tables)
    db.delete(video)
    db.commit()

    # Clean storage assets
    storage.delete_file(video_key)
    for f_key in frame_keys:
        storage.delete_file(f_key)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
