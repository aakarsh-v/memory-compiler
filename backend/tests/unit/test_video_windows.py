from app.pipeline.windows import generate_sliding_windows
from app.ml.video_encoder import VideoWindowEncoder
from app.db.models import Frame


def test_generate_sliding_windows():
    # 5.0s video with 4.0s window and 2.0s stride -> [0.0, 4.0] and [2.0, 5.0]
    windows = generate_sliding_windows(5.0, window_duration=4.0, stride=2.0)
    assert len(windows) == 2
    assert windows[0].start_seconds == 0.0
    assert windows[0].end_seconds == 4.0
    assert windows[1].start_seconds == 2.0
    assert windows[1].end_seconds == 5.0


def test_generate_windows_short_video():
    # Video shorter than window duration: 2.5s duration with 4.0s window -> single [0.0, 2.5] window
    windows = generate_sliding_windows(2.5, window_duration=4.0, stride=2.0)
    assert len(windows) == 1
    assert windows[0].start_seconds == 0.0
    assert windows[0].end_seconds == 2.5


def test_video_window_encoder_pooling():
    encoder = VideoWindowEncoder(dimension=4)
    f1 = Frame(embedding=[1.0, 0.0, 0.0, 0.0])
    f2 = Frame(embedding=[0.0, 1.0, 0.0, 0.0])

    pooled_vec = encoder.encode_window([f1, f2])
    assert len(pooled_vec) == 4
    # Equal contribution in dimensions 0 and 1
    assert abs(pooled_vec[0] - pooled_vec[1]) < 1e-5
    # Unit normalized
    norm = sum(x * x for x in pooled_vec)
    assert abs(norm - 1.0) < 1e-5

