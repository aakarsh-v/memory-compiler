import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.models import Base, Video, ProcessingJob, Frame
from app.db.session import get_db
from app.api.v1.videos import get_storage_service as get_video_storage
from app.api.v1.frames import get_storage_service as get_frame_storage
from app.storage.local import LocalStorageService
from app.pipeline.processor import VideoPipelineProcessor
from tests.fixtures.synthetic_media import create_synthetic_video


@pytest.fixture
def stream_test_env(tmp_path: Path):
    db_file = tmp_path / "stream_test.db"
    test_engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    storage_root = tmp_path / "media"
    storage = LocalStorageService(storage_root)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    def override_storage():
        return storage

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_video_storage] = override_storage
    app.dependency_overrides[get_frame_storage] = override_storage

    # Create and index fixture video
    raw_video = tmp_path / "stream_clip.mp4"
    create_synthetic_video(raw_video, duration_seconds=5, width=320, height=240)

    video_id = str(uuid.uuid4())
    storage_key = f"alice/{video_id}.mp4"
    with open(raw_video, "rb") as f:
        storage.save_file(f, storage_key)

    db = TestingSession()
    video = Video(
        id=video_id,
        owner_id="alice",
        filename="stream_clip.mp4",
        storage_key=storage_key,
        mime_type="video/mp4",
        size_bytes=raw_video.stat().st_size,
        status="QUEUED"
    )
    job = ProcessingJob(id=str(uuid.uuid4()), video_id=video_id, status="QUEUED")
    db.add(video)
    db.add(job)
    db.commit()

    processor = VideoPipelineProcessor(db, storage)
    processor.process_video(video_id)

    first_frame = db.query(Frame).filter(Frame.video_id == video_id).first()
    first_frame_id = first_frame.id
    db.close()

    client = TestClient(app)
    yield client, video_id, first_frame_id

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def test_stream_video_full_content(stream_test_env):
    client, video_id, _ = stream_test_env
    response = client.get(
        f"/api/v1/videos/{video_id}/stream",
        headers={"X-User-ID": "alice"}
    )
    assert response.status_code == 200
    assert response.headers["Accept-Ranges"] == "bytes"
    assert len(response.content) > 0


def test_stream_video_range_seek(stream_test_env):
    client, video_id, _ = stream_test_env
    # Request bytes 0 to 99 (100 bytes)
    response = client.get(
        f"/api/v1/videos/{video_id}/stream",
        headers={"X-User-ID": "alice", "Range": "bytes=0-99"}
    )
    assert response.status_code == 206
    assert response.headers["Content-Range"].startswith("bytes 0-99/")
    assert response.headers["Content-Length"] == "100"
    assert len(response.content) == 100


def test_stream_video_ownership_isolation(stream_test_env):
    client, video_id, _ = stream_test_env
    # Bob attempts to stream Alice's video -> 404
    response = client.get(
        f"/api/v1/videos/{video_id}/stream",
        headers={"X-User-ID": "bob"}
    )
    assert response.status_code == 404


def test_thumbnail_retrieval(stream_test_env):
    client, _, frame_id = stream_test_env
    response = client.get(
        f"/api/v1/frames/{frame_id}/thumbnail",
        headers={"X-User-ID": "alice"}
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "image/jpeg"
    assert len(response.content) > 0


def test_thumbnail_ownership_isolation(stream_test_env):
    client, _, frame_id = stream_test_env
    response = client.get(
        f"/api/v1/frames/{frame_id}/thumbnail",
        headers={"X-User-ID": "bob"}
    )
    assert response.status_code == 404

