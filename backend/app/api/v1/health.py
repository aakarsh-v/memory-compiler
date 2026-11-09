from fastapi import APIRouter, Response, status
from typing import Dict, Any

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health/live", status_code=status.HTTP_200_OK)
def liveness() -> Dict[str, str]:
    """Process liveness probe."""
    return {"status": "ok"}


@router.get("/health/ready")
def readiness(response: Response) -> Dict[str, Any]:
    """Readiness probe checking environment and critical resources."""
    checks = {
        "storage": False,
        "environment": settings.APP_ENV,
        "embedding_provider": settings.EMBEDDING_PROVIDER
    }

    # Verify storage root is accessible/creatable
    try:
        settings.MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
        checks["storage"] = True
    except Exception:
        checks["storage"] = False

    is_ready = checks["storage"]
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unhealthy", "checks": checks}

    return {"status": "ready", "checks": checks}

