import sys
from pathlib import Path

# Add scripts directory
scripts_dir = Path(__file__).resolve().parents[3] / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from evaluate_retrieval import compute_tiou, run_benchmark


def test_tiou_exact_match():
    # Complete overlap: [2.0, 4.0] and [2.0, 4.0] -> 1.0
    assert compute_tiou(2.0, 4.0, 2.0, 4.0) == 1.0


def test_tiou_disjoint():
    # No overlap: [0.0, 2.0] and [3.0, 5.0] -> 0.0
    assert compute_tiou(0.0, 2.0, 3.0, 5.0) == 0.0


def test_tiou_partial_overlap():
    # Intersection: [2.0, 4.0] (length 2.0), Union: [1.0, 5.0] (length 4.0) -> 0.5
    assert compute_tiou(1.0, 4.0, 2.0, 5.0) == 0.5


def test_benchmark_run(tmp_path: Path):
    report = run_benchmark(tmp_storage_dir=tmp_path)
    assert "metrics" in report
    assert "recall@1" in report["metrics"]
    assert "mean_tiou" in report["metrics"]
    assert "mean_latency_ms" in report["metrics"]
    assert report["metadata"]["embedding_provider"] == "mock"
