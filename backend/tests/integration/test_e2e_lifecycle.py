import io
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.models import Base, Video, ProcessingJob, Frame, VideoWindow, Event
from app.db.session import get_db
from app.api.v1.videos import get_storage_service as get_video_storage
from app.api.v1.frames import get_storage_service as get_frame_storage
from app.storage.local import LocalStorageService
from app.pipeline.processor import VideoPipelineProcessor
from tests.fixtures.synthetic_media import create_synthetic_video


@pytest.fixture
def e2e_env(tmp_path: Path):
    db_file = tmp_path / "e2e_test.db"
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

    client = TestClient(app)
    yield client, TestingSession, storage, tmp_path

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def test_full_lifecycle_and_clean_deletion(e2e_env):
    client, Session, storage, tmp_path = e2e_env

    # 1. Create synthetic fixture video
    fixture_video = tmp_path / "e2e_fixture.mp4"
    create_synthetic_video(fixture_video, duration_seconds=5, width=320, height=240)
    video_bytes = fixture_video.read_bytes()

    # 2. Upload video as Alice (POST /api/v1/videos) -> 202 Accepted
    upload_resp = client.post(
        "/api/v1/videos",
        files={"file": ("e2e_fixture.mp4", io.BytesIO(video_bytes), "video/mp4")},
        headers={"X-User-ID": "alice"}
    )
    assert upload_resp.status_code == 202
    data = upload_resp.json()
    video_id = data["video_id"]
    assert data["status"] == "queued"

    # 3. Execute video indexing pipeline
    db = Session()
    processor = VideoPipelineProcessor(db, storage)
    processor.process_video(video_id)
    db.close()

    # 4. Verify status polling -> 200 READY
    status_resp = client.get(f"/api/v1/videos/{video_id}/status", headers={"X-User-ID": "alice"})
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "READY"
    assert status_resp.json()["progress"] == 1.0

    # 5. Natural-language search (POST /api/v1/search)
    search_resp = client.post(
        "/api/v1/search",
        json={"query": "test pattern with crosshairs and calibration"},
        headers={"X-User-ID": "alice"}
    )
    assert search_resp.status_code == 200
    results = search_resp.json()["results"]
    assert len(results) > 0
    top_hit = results[0]
    assert top_hit["video_id"] == video_id
    evidence_ts = top_hit["evidence_timestamp_seconds"]
    thumbnail_url = top_hit["thumbnail_url"]

    # 6. Stream video seeking with Range header
    stream_resp = client.get(
        f"/api/v1/videos/{video_id}/stream",
        headers={"X-User-ID": "alice", "Range": "bytes=0-1024"}
    )
    assert stream_resp.status_code == 206
    assert "bytes 0-1024/" in stream_resp.headers["Content-Range"]

    # 7. Fetch thumbnail preview
    frame_id = top_hit["evidence"][0]["frame_id"]
    thumb_resp = client.get(
        f"/api/v1/frames/{frame_id}/thumbnail",
        headers={"X-User-ID": "alice"}
    )
    assert thumb_resp.status_code == 200
    assert thumb_resp.headers["Content-Type"] == "image/jpeg"

    # 8. Cross-User Security Check: Bob cannot access Alice's resources
    assert client.get(f"/api/v1/videos/{video_id}", headers={"X-User-ID": "bob"}).status_code == 404
    assert client.get(f"/api/v1/videos/{video_id}/stream", headers={"X-User-ID": "bob"}).status_code == 404
    assert client.get(f"/api/v1/frames/{frame_id}/thumbnail", headers={"X-User-ID": "bob"}).status_code == 404
    assert client.delete(f"/api/v1/videos/{video_id}", headers={"X-User-ID": "bob"}).status_code == 404

    # 9. Cascading Deletion (DELETE /api/v1/videos/{video_id}) -> 204 No Content
    del_resp = client.delete(f"/api/v1/videos/{video_id}", headers={"X-User-ID": "alice"})
    assert del_resp.status_code == 204

    # 10. Verify Zero Orphan Database Records
    db = Session()
    assert db.query(Video).filter(Video.id == video_id).count() == 0
    assert db.query(ProcessingJob).filter(ProcessingJob.video_id == video_id).count() == 0
    assert db.query(Frame).filter(Frame.video_id == video_id).count() == 0
    assert db.query(VideoWindow).filter(VideoWindow.video_id == video_id).count() == 0
    assert db.query(Event).filter(Event.video_id == video_id).count() == 0
    db.close()

    # 11. Verify Zero Orphan Files on Storage
    assert storage.exists(f"alice/{video_id}.mp4") is False
    # Verify frame image directory is clean
    frame_files_left = list((tmp_path / "media" / "alice" / "frames" / video_id).glob("*.jpg")) if (tmp_path / "media" / "alice" / "frames" / video_id).exists() else []
    assert len(frame_files_left) == 0

