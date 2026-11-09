"""
Demo Data Seeder for Memory Compiler.
Generates synthetic media clips, runs the pipeline, and indexes frames and temporal windows.
"""
import sys
import uuid
from pathlib import Path

# Add backend directory
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.db.session import SessionLocal, init_db
from app.db.models import Video, ProcessingJob
from app.storage.local import LocalStorageService
from app.pipeline.processor import VideoPipelineProcessor
from tests.fixtures.synthetic_media import create_synthetic_video


DEMO_VIDEOS = [
    {
        "filename": "demo_testpattern.mp4",
        "duration": 5,
        "description": "Calibration test pattern with color bars and tone",
    },
    {
        "filename": "demo_sequence.mp4",
        "duration": 6,
        "description": "Dynamic visual sequence with moving elements",
    }
]


def seed_demo(owner_id: str = "default_user") -> None:
    print(f"[*] Seeding demo data for owner: {owner_id}")
    init_db()

    db = SessionLocal()
    storage = LocalStorageService(settings.MEDIA_ROOT)
    processor = VideoPipelineProcessor(db, storage)

    temp_gen_dir = Path(settings.MEDIA_ROOT) / "tmp_gen"
    temp_gen_dir.mkdir(parents=True, exist_ok=True)

    for item in DEMO_VIDEOS:
        fname = item["filename"]
        raw_path = temp_gen_dir / fname
        create_synthetic_video(raw_path, duration_seconds=item["duration"], width=320, height=240)

        video_id = str(uuid.uuid4())
        storage_key = f"{owner_id}/{video_id}.mp4"

        with open(raw_path, "rb") as f:
            storage.save_file(f, storage_key)

        video = Video(
            id=video_id,
            owner_id=owner_id,
            filename=fname,
            storage_key=storage_key,
            mime_type="video/mp4",
            size_bytes=raw_path.stat().st_size,
            status="QUEUED"
        )
        job = ProcessingJob(id=str(uuid.uuid4()), video_id=video_id, status="QUEUED")
        db.add(video)
        db.add(job)
        db.commit()

        print(f"  -> Indexing video: {fname} (ID: {video_id})...")
        processed = processor.process_video(video_id)
        print(f"     Status: {processed.status}, Frames: {len(processed.frames)}, Windows: {len(processed.windows)}")

    # Clean temporary generated files
    for f in temp_gen_dir.glob("*.mp4"):
        try:
            f.unlink()
        except Exception:
            pass

    db.close()
    print("[+] Demo data seeded successfully! You can now start the API and search.")


if __name__ == "__main__":
    seed_demo()
