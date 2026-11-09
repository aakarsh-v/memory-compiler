from app.workers.celery_app import celery_app
from app.core.logging import logger
from app.db.session import SessionLocal
from app.storage.local import LocalStorageService
from app.core.config import settings
from app.pipeline.processor import VideoPipelineProcessor


def execute_video_processing(video_id: str) -> None:
    """Synchronous runner for video pipeline processing."""
    db = SessionLocal()
    storage = LocalStorageService(settings.MEDIA_ROOT)
    try:
        processor = VideoPipelineProcessor(db, storage)
        processor.process_video(video_id)
    finally:
        db.close()


@celery_app.task(name="process_video_task", bind=True, max_retries=2)
def process_video_task(self, video_id: str):
    """Celery background task for asynchronous video pipeline execution."""
    logger.info(f"Starting Celery task for video {video_id}", extra={"video_id": video_id})
    try:
        execute_video_processing(video_id)
    except Exception as exc:
        logger.exception(f"Celery task failed for video {video_id}: {str(exc)}")
        raise self.retry(exc=exc, countdown=5)

