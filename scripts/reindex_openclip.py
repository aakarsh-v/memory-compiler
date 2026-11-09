"""
Re-indexes all READY videos using the OpenCLIP embedding provider.
Run after switching EMBEDDING_PROVIDER from 'mock' to 'openclip'.

Usage:
    cd backend
    python ../scripts/reindex_openclip.py
"""
import os
import sys

# Force openclip provider regardless of .env for this script
os.environ["EMBEDDING_PROVIDER"] = "openclip"
os.environ["EMBEDDING_MODEL_ID"] = "ViT-B-32"
os.environ["EMBEDDING_DEVICE"] = "cpu"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")

from app.db.session import SessionLocal
from app.db.models import Video
from app.storage.local import LocalStorageService
from app.core.config import settings
from app.pipeline.processor import VideoPipelineProcessor


def main():
    db = SessionLocal()
    storage = LocalStorageService(settings.MEDIA_ROOT)
    processor = VideoPipelineProcessor(db, storage)

    videos = db.query(Video).filter(Video.status.in_(["READY", "FAILED", "QUEUED"])).all()
    print(f"Re-indexing {len(videos)} video(s) with OpenCLIP (ViT-B-32)...")

    for v in videos:
        print(f"\n  [{v.id[:8]}] {v.filename}")
        # Reset to QUEUED so processor picks it up fresh
        v.status = "QUEUED"
        v.progress = 0.0
        db.commit()

        result = processor.process_video(v.id)
        frame_model = result.frames[0].embedding_model if result.frames else "none"
        print(f"  -> status={result.status}  frames={len(result.frames)}  model={frame_model}")

    db.close()
    print("\nDone. All videos re-indexed with real OpenCLIP embeddings.")


if __name__ == "__main__":
    main()

