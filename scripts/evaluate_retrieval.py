"""
Retrieval evaluation script for Memory Compiler.
Measures Recall@K, temporal IoU (tIoU), and latency against a labeled benchmark.
"""
import json
import time
import uuid
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.models import Base, Video, ProcessingJob
from app.storage.local import LocalStorageService
from app.ml.factory import get_embedding_provider
from app.pipeline.processor import VideoPipelineProcessor
from app.services.search_service import SearchService
from app.schemas.search import SearchRequest
from tests.fixtures.synthetic_media import create_synthetic_video


def compute_tiou(pred_start: float, pred_end: float, gt_start: float, gt_end: float) -> float:
    """Calculates temporal Intersection over Union (tIoU) between two intervals."""
    inter_start = max(pred_start, gt_start)
    inter_end = min(pred_end, gt_end)
    intersection = max(0.0, inter_end - inter_start)

    union_start = min(pred_start, gt_start)
    union_end = max(pred_end, gt_end)
    union = max(1e-6, union_end - union_start)

    return round(intersection / union, 4)


BENCHMARK_QUERIES = [
    {
        "query": "test pattern with crosshairs and colors",
        "query_type": "object_scene",
        "gt_start": 0.0,
        "gt_end": 4.0,
        "expected_match": True
    },
    {
        "query": "colorful visual bars and tone calibration",
        "query_type": "attribute",
        "gt_start": 1.0,
        "gt_end": 3.0,
        "expected_match": True
    },
    {
        "query": "rapid flashing animation test sequence",
        "query_type": "single_action",
        "gt_start": 2.0,
        "gt_end": 5.0,
        "expected_match": True
    },
    {
        "query": "astronaut walking on lunar surface with rover",
        "query_type": "hard_negative",
        "gt_start": None,
        "gt_end": None,
        "expected_match": False
    }
]


def run_benchmark(tmp_storage_dir: Path = None) -> Dict[str, Any]:
    if tmp_storage_dir is None:
        tmp_storage_dir = Path(settings.MEDIA_ROOT) / "eval_tmp"
    tmp_storage_dir.mkdir(parents=True, exist_ok=True)

    # Isolated database
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    storage = LocalStorageService(tmp_storage_dir)

    # 1. Create and index synthetic benchmark video
    video_file = tmp_storage_dir / "bench_video.mp4"
    create_synthetic_video(video_file, duration_seconds=5, width=320, height=240)

    video_id = str(uuid.uuid4())
    storage_key = f"eval_user/{video_id}.mp4"
    with open(video_file, "rb") as f:
        storage.save_file(f, storage_key)

    video = Video(
        id=video_id,
        owner_id="eval_user",
        filename="bench_video.mp4",
        storage_key=storage_key,
        mime_type="video/mp4",
        size_bytes=video_file.stat().st_size,
        status="QUEUED"
    )
    job = ProcessingJob(id=str(uuid.uuid4()), video_id=video_id, status="QUEUED")
    db.add(video)
    db.add(job)
    db.commit()

    start_index = time.perf_counter()
    processor = VideoPipelineProcessor(db, storage)
    processor.process_video(video_id)
    indexing_time_sec = time.perf_counter() - start_index

    # 2. Comparative Evaluation across Search Modes (Phase 5)
    provider = get_embedding_provider()
    search_service = SearchService(db, provider)

    search_modes = ["frame_semantic_v1", "video_window_v1", "hybrid_v1"]
    comparative_results = {}

    for mode in search_modes:
        r1_hits = 0
        r3_hits = 0
        r5_hits = 0
        positive_count = 0
        tiou_scores = []
        latencies_ms = []

        per_query_results = []

        for bq in BENCHMARK_QUERIES:
            query_text = bq["query"]
            expected_match = bq["expected_match"]

            t0 = time.perf_counter()
            req = SearchRequest(query=query_text, limit=5, search_mode=mode)
            response = search_service.search(req, owner_id="eval_user")
            elapsed_ms = (time.perf_counter() - t0) * 1000
            latencies_ms.append(elapsed_ms)

            results = response.results
            matched_at_rank = None
            best_tiou = 0.0

            if expected_match:
                positive_count += 1
                gt_start = bq["gt_start"]
                gt_end = bq["gt_end"]

                for rank, r in enumerate(results, start=1):
                    tiou = compute_tiou(r.start_seconds, r.end_seconds, gt_start, gt_end)
                    if tiou >= 0.2:
                        if matched_at_rank is None:
                            matched_at_rank = rank
                            best_tiou = tiou

                if matched_at_rank is not None:
                    if matched_at_rank <= 1:
                        r1_hits += 1
                    if matched_at_rank <= 3:
                        r3_hits += 1
                    if matched_at_rank <= 5:
                        r5_hits += 1
                    tiou_scores.append(best_tiou)
                else:
                    tiou_scores.append(0.0)

            per_query_results.append({
                "query": query_text,
                "type": bq["query_type"],
                "expected_match": expected_match,
                "results_count": len(results),
                "matched_rank": matched_at_rank,
                "best_tiou": best_tiou,
                "latency_ms": round(elapsed_ms, 2)
            })

        recall_1 = round(r1_hits / positive_count, 3) if positive_count else 0.0
        recall_3 = round(r3_hits / positive_count, 3) if positive_count else 0.0
        recall_5 = round(r5_hits / positive_count, 3) if positive_count else 0.0
        mean_tiou = round(sum(tiou_scores) / len(tiou_scores), 3) if tiou_scores else 0.0
        mean_latency = round(sum(latencies_ms) / len(latencies_ms), 2)

        comparative_results[mode] = {
            "metrics": {
                "recall@1": recall_1,
                "recall@3": recall_3,
                "recall@5": recall_5,
                "mean_tiou": mean_tiou,
                "mean_latency_ms": mean_latency
            },
            "queries": per_query_results
        }

    report = {
        "metadata": {
            "embedding_provider": settings.EMBEDDING_PROVIDER,
            "model_id": settings.EMBEDDING_MODEL_ID,
            "frame_sample_seconds": settings.FRAME_SAMPLE_SECONDS,
            "vector_dimension": settings.VECTOR_DIMENSION,
            "indexing_time_sec": round(indexing_time_sec, 2),
            "queries_evaluated": len(BENCHMARK_QUERIES)
        },
        # Default top-level metrics report frame_semantic_v1 for backward compatibility
        "metrics": comparative_results["frame_semantic_v1"]["metrics"],
        "comparative_modes": comparative_results
    }

    db.close()
    return report


if __name__ == "__main__":
    print("=" * 60)
    print("Running Memory Compiler Retrieval Evaluation Benchmark...")
    print("=" * 60)
    report = run_benchmark()
    print(json.dumps(report, indent=2))

    # Save to data directory
    out_path = Path("data/evaluation_baseline.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n[+] Saved baseline benchmark report to {out_path}")
