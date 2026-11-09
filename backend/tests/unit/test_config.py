from app.core.config import Settings


def test_settings_defaults():
    s = Settings()
    assert s.APP_ENV == "development"
    assert s.MAX_UPLOAD_MB == 500
    assert s.max_upload_bytes == 500 * 1024 * 1024
    assert ".mp4" in s.ALLOWED_VIDEO_EXTENSIONS
    assert s.EMBEDDING_PROVIDER == "mock"
    assert s.VECTOR_DIMENSION == 512


def test_settings_custom_extensions():
    s = Settings(ALLOWED_VIDEO_EXTENSIONS=".mp4, .mkv, .avi ")
    assert s.ALLOWED_VIDEO_EXTENSIONS == [".mp4", ".mkv", ".avi"]
