import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.core.errors import AppException
from app.db.models import Video, ProcessingJob, Frame, VideoWindow
from app.storage.local import LocalStorageService
from app.pipeline.probing import probe_video, VideoMetadata
from app.pipeline.extraction import extract_frames, ExtractedFrame
from app.pipeline.windows import generate_sliding_windows
from app.ml.video_encoder import VideoWindowEncoder
from app.ml.factory import get_embedding_provider


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class VideoPipelineProcessor:
    """
    Coordinates media probing, frame extraction, storage persistence, and job state transitions.
    Guarantees retry-safety, honest progress checkpoints, and safe failure handling.
    """

    def __init__(self, db: Session, storage: LocalStorageService):
        self.db = db
        self.storage = storage

    def process_video(self, video_id: str) -> Video:
        video = self.db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise AppException("VIDEO_NOT_FOUND", f"Video {video_id} not found", status_code=404)

        job = (
            self.db.query(ProcessingJob)
            .filter(ProcessingJob.video_id == video_id)
            .order_by(ProcessingJob.created_at.desc())
            .first()
        )
        if not job:
            job = ProcessingJob(
                id=str(uuid.uuid4()),
                video_id=video_id,
                status="QUEUED",
                stage="QUEUED",
                progress=0.0
            )
            self.db.add(job)
            self.db.commit()

        try:
            # 1. Transition: PROBING
            video.status = "PROBING"
            video.current_stage = "PROBING"
            video.progress = 0.1
            job.status = "PROCESSING"
            job.stage = "PROBING"
            job.progress = 0.1
            job.started_at = utc_now()
            self.db.commit()

            # Resolve local media path from opaque key
            media_path = self.storage.get_path(video.storage_key)

            # Probe media streams with FFprobe
            metadata = probe_video(media_path)
            video.duration_seconds = metadata.duration_seconds
            video.width = metadata.width
            video.height = metadata.height
            video.fps = metadata.fps
            video.has_audio = metadata.has_audio
            self.db.commit()

            # 2. Transition: EXTRACTING_FRAMES
            video.status = "EXTRACTING_FRAMES"
            video.current_stage = "EXTRACTING_FRAMES"
            video.progress = 0.3
            job.stage = "EXTRACTING_FRAMES"
            job.progress = 0.3
            self.db.commit()

            # Extract frames with FFmpeg at configured sample interval
            extracted_frames = extract_frames(
                video_path=media_path,
                metadata=metadata,
                sample_interval=settings.FRAME_SAMPLE_SECONDS
            )

            # 3. Transition: EMBEDDING_FRAMES
            video.status = "EMBEDDING_FRAMES"
            video.current_stage = "EMBEDDING_FRAMES"
            video.progress = 0.6
            job.stage = "EMBEDDING_FRAMES"
            job.progress = 0.6
            self.db.commit()

            # Retrieve configured embedding provider
            embedding_provider = get_embedding_provider()

            # Batch frames for inference
            batch_size = max(1, settings.EMBEDDING_BATCH_SIZE)
            frame_image_paths = [f.image_path for f in extracted_frames]
            all_embeddings: List[List[float]] = []

            for i in range(0, len(frame_image_paths), batch_size):
                batch_paths = frame_image_paths[i : i + batch_size]
                batch_vectors = embedding_provider.embed_frames(batch_paths)
                all_embeddings.extend(batch_vectors)

            # 4. Transition: PERSISTING_INDEX
            video.status = "PERSISTING_INDEX"
            video.current_stage = "PERSISTING_INDEX"
            video.progress = 0.8
            job.stage = "PERSISTING_INDEX"
            job.progress = 0.8
            self.db.commit()

            # Clean any existing frames & windows for idempotency
            self.db.query(Frame).filter(Frame.video_id == video_id).delete()
            self.db.query(VideoWindow).filter(VideoWindow.video_id == video_id).delete()
            self.db.commit()

            frame_records: List[Frame] = []
            for frame, embedding_vec in zip(extracted_frames, all_embeddings):
                # Deterministic key: {owner_id}/frames/{video_id}/frame_{timestamp_ms:010d}.jpg
                ts_ms = int(round(frame.timestamp_seconds * 1000))
                frame_key = f"{video.owner_id}/frames/{video.id}/frame_{ts_ms:010d}.jpg"

                # Save frame image to storage
                with open(frame.image_path, "rb") as f:
                    self.storage.save_file(f, frame_key)

                frame_row = Frame(
                    id=str(uuid.uuid4()),
                    video_id=video.id,
                    timestamp_seconds=frame.timestamp_seconds,
                    image_key=frame_key,
                    width=frame.width,
                    height=frame.height,
                    embedding=embedding_vec,
                    embedding_model=embedding_provider.model_id,
                    preprocessing_version="v1"
                )
                frame_records.append(frame_row)

            self.db.add_all(frame_records)

            # Generate and persist temporal video-windows (Phase 5)
            window_encoder = VideoWindowEncoder(dimension=embedding_provider.dimension)
            temporal_windows = generate_sliding_windows(
                duration_seconds=video.duration_seconds or 0.0,
                window_duration=4.0,
                stride=2.0
            )

            window_records: List[VideoWindow] = []
            for tw in temporal_windows:
                # Find frames in window
                w_frames = [
                    f for f in frame_records
                    if tw.start_seconds <= f.timestamp_seconds <= tw.end_seconds
                ]
                w_vec = window_encoder.encode_window(w_frames)
                window_row = VideoWindow(
                    id=str(uuid.uuid4()),
                    video_id=video.id,
                    start_seconds=tw.start_seconds,
                    end_seconds=tw.end_seconds,
                    embedding=w_vec,
                    model_id=window_encoder.model_id
                )
                window_records.append(window_row)

            if window_records:
                self.db.add_all(window_records)

            # 5. Finalize READY
            video.status = "READY"
            video.current_stage = "COMPLETED"
            video.progress = 1.0
            video.error_code = None
            video.error_message = None

            job.status = "COMPLETED"
            job.stage = "COMPLETED"
            job.progress = 1.0
            job.finished_at = utc_now()
            job.error_summary = None

            self.db.commit()
            self.db.refresh(video)

            logger.info(
                f"Video {video_id} processed and indexed successfully ({len(frame_records)} frames with embeddings)",
                extra={"video_id": video_id, "job_id": job.id, "stage": "COMPLETED"}
            )
            return video

        except AppException as e:
            self.db.rollback()
            video.status = "FAILED"
            video.error_code = e.code
            video.error_message = e.message
            video.current_stage = "FAILED"

            job.status = "FAILED"
            job.error_summary = f"[{e.code}] {e.message}"
            job.finished_at = utc_now()
            self.db.commit()
            logger.warning(
                f"Video {video_id} processing failed: [{e.code}] {e.message}",
                extra={"video_id": video_id, "job_id": job.id, "error_code": e.code}
            )
            return video

        except Exception as e:
            self.db.rollback()
            video.status = "FAILED"
            video.error_code = "PROCESSING_UNHANDLED_ERROR"
            video.error_message = "An unexpected error occurred during media processing"
            video.current_stage = "FAILED"

            job.status = "FAILED"
            job.error_summary = str(e)
            job.finished_at = utc_now()
            self.db.commit()
            logger.exception(
                f"Unhandled error processing video {video_id}: {str(e)}",
                extra={"video_id": video_id, "job_id": job.id, "error_code": "PROCESSING_UNHANDLED_ERROR"}
            )
            return video

