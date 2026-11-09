import io
import pytest
from pathlib import Path

from app.storage.local import LocalStorageService
from app.core.errors import ValidationException


def test_storage_save_and_retrieve(tmp_path: Path):
    storage = LocalStorageService(tmp_path)
    data = b"Sample video content bytes"
    stream = io.BytesIO(data)

    key = "user1/video123.mp4"
    path = storage.save_file(stream, key)

    assert path.exists()
    assert path.read_bytes() == data
    assert storage.exists(key) is True
    assert storage.get_path(key) == path


def test_storage_path_traversal_rejection(tmp_path: Path):
    storage = LocalStorageService(tmp_path)
    stream = io.BytesIO(b"malicious")

    # Reject '..' traversal
    with pytest.raises(ValidationException) as exc:
        storage.save_file(stream, "../outside.mp4")
    assert "STORAGE_INVALID_KEY" in exc.value.code

    # Reject root escape
    with pytest.raises(ValidationException) as exc:
        storage.save_file(stream, "/etc/passwd")
    assert "STORAGE_INVALID_KEY" in exc.value.code


def test_storage_delete(tmp_path: Path):
    storage = LocalStorageService(tmp_path)
    stream = io.BytesIO(b"to be deleted")
    key = "user1/delete_me.mp4"
    storage.save_file(stream, key)

    assert storage.exists(key) is True
    assert storage.delete_file(key) is True
    assert storage.exists(key) is False

