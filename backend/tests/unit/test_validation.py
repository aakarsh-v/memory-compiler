import pytest
from app.services.job_service import JobService
from app.core.errors import ValidationException, PayloadTooLargeException


class DummyStorage:
    pass


def test_validate_allowed_extension():
    service = JobService(db=None, storage=DummyStorage())
    assert service.validate_upload("my_clip.mp4") == ".mp4"
    assert service.validate_upload("vacation.MOV") == ".mov"
    assert service.validate_upload("stream.webm") == ".webm"


def test_reject_unsupported_extension():
    service = JobService(db=None, storage=DummyStorage())
    with pytest.raises(ValidationException) as exc:
        service.validate_upload("payload.exe")
    assert exc.value.code == "VIDEO_UNSUPPORTED_FORMAT"


def test_reject_empty_filename():
    service = JobService(db=None, storage=DummyStorage())
    with pytest.raises(ValidationException) as exc:
        service.validate_upload("")
    assert exc.value.code == "VIDEO_INVALID_FILENAME"


def test_reject_oversized_payload():
    service = JobService(db=None, storage=DummyStorage())
    oversized_bytes = 600 * 1024 * 1024  # 600MB when limit is 500MB
    with pytest.raises(PayloadTooLargeException) as exc:
        service.validate_upload("big_video.mp4", file_size=oversized_bytes)
    assert exc.value.code == "VIDEO_TOO_LARGE"

