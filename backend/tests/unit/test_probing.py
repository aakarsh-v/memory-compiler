from pathlib import Path
import pytest

from app.pipeline.probing import probe_video, MediaProbeException
from tests.fixtures.synthetic_media import create_synthetic_video


@pytest.fixture
def sample_video(tmp_path: Path) -> Path:
    video_path = tmp_path / "sample_5s.mp4"
    return create_synthetic_video(video_path, duration_seconds=5, width=320, height=240)


def test_probe_valid_video(sample_video: Path):
    meta = probe_video(sample_video)
    assert abs(meta.duration_seconds - 5.0) < 0.2
    assert meta.width == 320
    assert meta.height == 240
    assert meta.fps == 30.0
    assert meta.has_audio is True
    assert "h264" in meta.codec_name.lower()


def test_probe_nonexistent_file(tmp_path: Path):
    with pytest.raises(MediaProbeException) as exc:
        probe_video(tmp_path / "missing.mp4")
    assert exc.value.code == "MEDIA_FILE_NOT_FOUND"


def test_probe_corrupt_file(tmp_path: Path):
    corrupt_file = tmp_path / "corrupt.mp4"
    corrupt_file.write_text("This is not a valid video file content at all")
    with pytest.raises(MediaProbeException) as exc:
        probe_video(corrupt_file)
    assert exc.value.code == "MEDIA_CORRUPT"
