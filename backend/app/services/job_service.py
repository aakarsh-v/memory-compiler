import uuid
from pathlib import Path
from typing import BinaryIO, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ValidationException, PayloadTooLargeException
from app.db.models import Video, ProcessingJob
from app.storage.local import LocalStorageService


class JobService:
    def __init__(self, db: Session, storage: LocalStorageService):
        self.db = db
        self.storage = storage

    def validate_upload(self, filename: str, content_type: Optional[str] = None, file_size: Optional[int] = None) -> str:
        """Validate filename extension and optional size limits."""
        if not filename:
            raise ValidationException("VIDEO_INVALID_FILENAME", "Filename cannot be empty")

        ext = Path(filename).suffix.lower()
        if ext not in settings.ALLOWED_VIDEO_EXTENSIONS:
            allowed = ", ".join(settings.ALLOWED_VIDEO_EXTENSIONS)
            raise ValidationException(
                "VIDEO_UNSUPPORTED_FORMAT",
                f"Video format '{ext}' is not supported. Allowed formats: {allowed}"
            )

        if file_size is not None and file_size > settings.max_upload_bytes:
            raise PayloadTooLargeException(
                "VIDEO_TOO_LARGE",
                f"Uploaded file exceeds maximum limit of {settings.MAX_UPLOAD_MB} MB"
            )

        return ext

    def create_video_and_job(
        self,
        stream: BinaryIO,
        filename: str,
        content_type: str,
        size_bytes: int,
        owner_id: str
    ) -> Video:
        """
        Atomically saves media stream to private storage, creates video record and initial job.
        """
        ext = self.validate_upload(filename, content_type=content_type, file_size=size_bytes)

        video_id = str(uuid.uuid4())
        # Opaque storage key: strictly isolated by owner_id and random uuid
        storage_key = f"{owner_id}/{video_id}{ext}"

        # Write to storage atomically
        self.storage.save_file(stream, storage_key)

        video = Video(
            id=video_id,
            owner_id=owner_id,
            filename=Path(filename).name,  # Sanitize to basename only
            storage_key=storage_key,
            mime_type=content_type or "application/octet-stream",
            size_bytes=size_bytes,
            status="QUEUED",
            current_stage="QUEUED",
            progress=0.0
        )
        self.db.add(video)

        job = ProcessingJob(
            id=str(uuid.uuid4()),
            video_id=video_id,
            status="QUEUED",
            stage="QUEUED",
            progress=0.0,
            attempt=1
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(video)

        # Attempt to enqueue async Celery worker task if explicitly enabled
        if settings.ENABLE_ASYNC_WORKER:
            try:
                from app.workers.tasks import process_video_task
                process_video_task.delay(video.id)
            except Exception:
                pass

        return video
