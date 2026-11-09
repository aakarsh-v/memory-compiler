import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.models import Base, Video, ProcessingJob
from app.db.session import get_db
from app.api.v1.videos import get_storage_service
from app.storage.local import LocalStorageService
from app.pipeline.processor import VideoPipelineProcessor
from tests.fixtures.synthetic_media import create_synthetic_video


@pytest.fixture
def search_test_env(tmp_path: Path):
    db_file = tmp_path / "search_test.db"
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
    app.dependency_overrides[get_storage_service] = override_storage

    # Create and index an actual fixture video for Alice
    raw_video = tmp_path / "alice_walk.mp4"
    create_synthetic_video(raw_video, duration_seconds=5, width=320, height=240)

    alice_video_id = str(uuid.uuid4())
    storage_key = f"alice/{alice_video_id}.mp4"
    with open(raw_video, "rb") as f:
        storage.save_file(f, storage_key)

    db = TestingSession()
    video = Video(
        id=alice_video_id,
        owner_id="alice",
        filename="alice_walk.mp4",
        storage_key=storage_key,
        mime_type="video/mp4",
        size_bytes=raw_video.stat().st_size,
        status="QUEUED"
    )
    job = ProcessingJob(
        id=str(uuid.uuid4()),
        video_id=alice_video_id,
        status="QUEUED"
    )
    db.add(video)
    db.add(job)
    db.commit()

    # Run processor to index frames with mock vectors
    processor = VideoPipelineProcessor(db, storage)
    processor.process_video(alice_video_id)
    db.close()

    client = TestClient(app)
    yield client, alice_video_id

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def test_search_endpoint_contract(search_test_env):
    client, alice_video_id = search_test_env

    # Alice searches her video
    payload = {
        "query": "person walking in hallway",
        "limit": 5,
        "include_evidence": True
    }
    response = client.post(
        "/api/v1/search",
        json=payload,
        headers={"X-User-ID": "alice"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "person walking in hallway"
    assert data["search_mode"] == "frame_semantic_v1"
    assert len(data["results"]) > 0

    first_result = data["results"][0]
    assert first_result["video_id"] == alice_video_id
    assert first_result["filename"] == "alice_walk.mp4"
    assert "start_seconds" in first_result
    assert "end_seconds" in first_result
    assert "evidence_timestamp_seconds" in first_result
    assert first_result["thumbnail_url"].startswith("/api/v1/frames/")
    assert first_result["score_type"] == "cosine_similarity"
    assert isinstance(first_result["score"], float)
    assert len(first_result["evidence"]) > 0


def test_search_ownership_isolation(search_test_env):
    client, _ = search_test_env

    # Bob searches -> Alice's video must NOT appear
    response = client.post(
        "/api/v1/search",
        json={"query": "person walking in hallway"},
        headers={"X-User-ID": "bob"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 0
