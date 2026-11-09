import io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.models import Base
from app.db.session import get_db
from app.api.v1.videos import get_storage_service
from app.storage.local import LocalStorageService


@pytest.fixture
def test_env(tmp_path: Path):
    # Setup SQLite in-memory engine for test isolation
    test_engine = create_engine(
        f"sqlite:///{tmp_path}/test.db",
        connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    storage_dir = tmp_path / "media"
    storage_service = LocalStorageService(storage_dir)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def override_get_storage():
        return storage_service

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage_service] = override_get_storage

    client = TestClient(app)
    yield client, storage_service

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def test_upload_success_and_status(test_env):
    client, _ = test_env
    video_content = b"fake mp4 video content header and stream"

    response = client.post(
        "/api/v1/videos",
        files={"file": ("test_clip.mp4", io.BytesIO(video_content), "video/mp4")},
        headers={"X-User-ID": "user-alice"}
    )

    assert response.status_code == 202
    data = response.json()
    assert "video_id" in data
    assert data["status"] == "queued"
    assert data["status_url"] == f"/api/v1/videos/{data['video_id']}/status"

    video_id = data["video_id"]

    # Poll status
    status_resp = client.get(
        f"/api/v1/videos/{video_id}/status",
        headers={"X-User-ID": "user-alice"}
    )
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["video_id"] == video_id
    assert status_data["status"] == "QUEUED"
    assert status_data["current_stage"] == "QUEUED"
    assert status_data["progress"] == 0.0

    # Get detail
    detail_resp = client.get(
        f"/api/v1/videos/{video_id}",
        headers={"X-User-ID": "user-alice"}
    )
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["filename"] == "test_clip.mp4"
    assert detail_data["owner_id"] == "user-alice"
    assert detail_data["size_bytes"] == len(video_content)


def test_upload_unsupported_format(test_env):
    client, _ = test_env
    response = client.post(
        "/api/v1/videos",
        files={"file": ("malicious.exe", io.BytesIO(b"binary"), "application/octet-stream")},
        headers={"X-User-ID": "user-alice"}
    )
    assert response.status_code == 400
    err = response.json()
    assert "error" in err
    assert err["error"]["code"] == "VIDEO_UNSUPPORTED_FORMAT"
    assert "request_id" in err["error"]


def test_ownership_isolation(test_env):
    client, _ = test_env

    # Alice uploads a video
    resp_alice = client.post(
        "/api/v1/videos",
        files={"file": ("alice_family.mp4", io.BytesIO(b"alice clip"), "video/mp4")},
        headers={"X-User-ID": "alice"}
    )
    assert resp_alice.status_code == 202
    alice_video_id = resp_alice.json()["video_id"]

    # Bob uploads a video
    resp_bob = client.post(
        "/api/v1/videos",
        files={"file": ("bob_holiday.mp4", io.BytesIO(b"bob clip"), "video/mp4")},
        headers={"X-User-ID": "bob"}
    )
    assert resp_bob.status_code == 202
    bob_video_id = resp_bob.json()["video_id"]

    # Alice lists videos -> only sees her video
    alice_list = client.get("/api/v1/videos", headers={"X-User-ID": "alice"}).json()
    alice_ids = [v["id"] for v in alice_list["items"]]
    assert alice_video_id in alice_ids
    assert bob_video_id not in alice_ids

    # Bob lists videos -> only sees his video
    bob_list = client.get("/api/v1/videos", headers={"X-User-ID": "bob"}).json()
    bob_ids = [v["id"] for v in bob_list["items"]]
    assert bob_video_id in bob_ids
    assert alice_video_id not in bob_ids

    # Bob cannot query Alice's video detail or status (returns 404)
    bob_query_alice = client.get(f"/api/v1/videos/{alice_video_id}", headers={"X-User-ID": "bob"})
    assert bob_query_alice.status_code == 404
    assert bob_query_alice.json()["error"]["code"] == "VIDEO_NOT_FOUND"

    bob_query_alice_status = client.get(f"/api/v1/videos/{alice_video_id}/status", headers={"X-User-ID": "bob"})
    assert bob_query_alice_status.status_code == 404

