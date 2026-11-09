import uuid
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, Video, ProcessingJob, Frame
from app.storage.local import LocalStorageService
from app.pipeline.processor import VideoPipelineProcessor
from tests.fixtures.synthetic_media import create_synthetic_video


@pytest.fixture
def env(tmp_path: Path):
    db_file = tmp_path / "test_pipeline.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()

    storage_root = tmp_path / "media"
    storage = LocalStorageService(storage_root)

    yield db, storage

    db.close()
    Base.metadata.drop_all(bind=engine)


def test_process_video_end_to_end(env, tmp_path: Path):
    db, storage = env

    # 1. Create synthetic fixture video
    raw_video_path = tmp_path / "clip.mp4"
    create_synthetic_video(raw_video_path, duration_seconds=5, width=320, height=240)

    # 2. Save to storage
    video_id = str(uuid.uuid4())
    storage_key = f"alice/{video_id}.mp4"
    with open(raw_video_path, "rb") as f:
        storage.save_file(f, storage_key)

    # 3. Create Video & Job records
    video = Video(
        id=video_id,
        owner_id="alice",
        filename="clip.mp4",
        storage_key=storage_key,
        mime_type="video/mp4",
        size_bytes=raw_video_path.stat().st_size,
        status="QUEUED",
        current_stage="QUEUED",
        progress=0.0
    )
    job = ProcessingJob(
        id=str(uuid.uuid4()),
        video_id=video_id,
        status="QUEUED",
        stage="QUEUED",
        progress=0.0
    )
    db.add(video)
    db.add(job)
    db.commit()

    # 4. Execute pipeline processor
    processor = VideoPipelineProcessor(db, storage)
    processed = processor.process_video(video_id)

    assert processed.status == "READY"
    assert processed.current_stage == "COMPLETED"
    assert processed.progress == 1.0
    assert abs(processed.duration_seconds - 5.0) < 0.2
    assert processed.width == 320
    assert processed.height == 240
    assert processed.fps == 30.0
    assert processed.has_audio is True

    # Check Frame records in database
    frames = db.query(Frame).filter(Frame.video_id == video_id).order_by(Frame.timestamp_seconds).all()
    assert len(frames) == 3
    timestamps = [f.timestamp_seconds for f in frames]
    assert timestamps == [0.0, 2.0, 4.0]

    for f in frames:
        assert storage.exists(f.image_key) is True
        assert f.width == 320
        assert f.height == 240
        assert f.embedding_model == "mock-clip-vit-b32"
        assert f.preprocessing_version == "v1"

    # 5. Test IDEMPOTENCY / RETRY-SAFETY
    # Re-running process_video should re-extract without creating duplicate records
    rerun_processed = processor.process_video(video_id)
    assert rerun_processed.status == "READY"

    frames_after_rerun = db.query(Frame).filter(Frame.video_id == video_id).all()
    assert len(frames_after_rerun) == 3  # Still exactly 3 frames, no duplicates


def test_process_corrupt_video_failure(env, tmp_path: Path):
    db, storage = env

    corrupt_file = tmp_path / "corrupt.mp4"
    corrupt_file.write_text("invalid video stream header")

    video_id = str(uuid.uuid4())
    storage_key = f"alice/{video_id}.mp4"
    with open(corrupt_file, "rb") as f:
        storage.save_file(f, storage_key)

    video = Video(
        id=video_id,
        owner_id="alice",
        filename="corrupt.mp4",
        storage_key=storage_key,
        mime_type="video/mp4",
        size_bytes=corrupt_file.stat().st_size,
        status="QUEUED"
    )
    db.add(video)
    db.commit()

    processor = VideoPipelineProcessor(db, storage)
    failed_video = processor.process_video(video_id)

    assert failed_video.status == "FAILED"
    assert failed_video.error_code == "MEDIA_CORRUPT"
    assert failed_video.current_stage == "FAILED"

    # Verify no frames were persisted
    frames = db.query(Frame).filter(Frame.video_id == video_id).all()
    assert len(frames) == 0
