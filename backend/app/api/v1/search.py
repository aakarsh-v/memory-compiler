from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.ml.factory import get_embedding_provider
from app.schemas.search import SearchRequest, SearchResponse
from app.services.search_service import SearchService

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def search_videos(
    request: SearchRequest,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_user_id)
) -> SearchResponse:
    """
    Natural-language visual search across owner's indexed READY videos.
    Returns ranked time-interval candidates with evidence timestamps and thumbnails.
    """
    provider = get_embedding_provider()
    search_service = SearchService(db, provider)
    return search_service.search(request, owner_id)

