from pathlib import Path
import pytest

from app.pipeline.probing import probe_video
from app.pipeline.extraction import extract_frames
from tests.fixtures.synthetic_media import create_synthetic_video


@pytest.fixture
def sample_video(tmp_path: Path) -> Path:
    video_path = tmp_path / "sample_5s.mp4"
    return create_synthetic_video(video_path, duration_seconds=5, width=320, height=240)


def test_extract_frames_monotonic_timestamps(sample_video: Path):
    meta = probe_video(sample_video)
    frames = extract_frames(sample_video, meta, sample_interval=2.0)

    # 5 second video with 2.0s interval yields 3 frames: ~0.0s, 2.0s, 4.0s
    assert len(frames) == 3

    timestamps = [f.timestamp_seconds for f in frames]
    assert timestamps == sorted(timestamps)  # Monotonic
    assert timestamps[0] == 0.0
    assert timestamps[1] == 2.0
    assert timestamps[2] == 4.0

    # Verify frame image properties
    for frame in frames:
        assert frame.image_path.exists()
        assert frame.width == 320
        assert frame.height == 240
