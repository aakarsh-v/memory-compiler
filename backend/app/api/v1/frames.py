from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.core.config import settings
from app.core.errors import NotFoundException
from app.db.session import get_db
from app.db.models import Frame, Video
from app.storage.local import LocalStorageService

router = APIRouter(prefix="/api/v1/frames", tags=["frames"])


def get_storage_service() -> LocalStorageService:
    return LocalStorageService(settings.MEDIA_ROOT)


@router.get("/{frame_id}/thumbnail")
def get_frame_thumbnail(
    frame_id: str,
    db: Session = Depends(get_db),
    storage: LocalStorageService = Depends(get_storage_service),
    owner_id: str = Depends(get_current_user_id)
) -> FileResponse:
    """Streams thumbnail image for a specific evidence frame, enforcing media ownership."""
    frame_record = (
        db.query(Frame, Video)
        .join(Video, Frame.video_id == Video.id)
        .filter(Frame.id == frame_id, Video.owner_id == owner_id)
        .first()
    )

    if not frame_record:
        raise NotFoundException("FRAME_NOT_FOUND", f"Frame '{frame_id}' not found or access denied")

    frame, _ = frame_record
    file_path = storage.get_path(frame.image_key)

    return FileResponse(
        path=file_path,
        media_type="image/jpeg",
        filename=f"frame_{frame_id}.jpg"
    )
