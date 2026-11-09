import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List
from PIL import Image

from app.core.config import settings
from app.core.errors import AppException
from app.core.logging import logger
from app.pipeline.probing import VideoMetadata


class FrameExtractionException(AppException):
    def __init__(self, code: str, message: str):
        super().__init__(code=code, message=message, status_code=500)


@dataclass
class ExtractedFrame:
    timestamp_seconds: float
    image_path: Path
    width: int
    height: int


def extract_frames(
    video_path: Path,
    metadata: VideoMetadata,
    sample_interval: float = None,
    timeout_seconds: int = 120
) -> List[ExtractedFrame]:
    """
    Extracts timestamped frames at configurable intervals using ffmpeg.
    Timestamps represent float seconds on the media presentation timeline.
    """
    if sample_interval is None:
        sample_interval = settings.FRAME_SAMPLE_SECONDS

    if sample_interval <= 0:
        raise FrameExtractionException("INVALID_SAMPLE_INTERVAL", "Sample interval must be positive")

    temp_dir = Path(tempfile.mkdtemp(prefix="mc_frames_"))
    output_pattern = temp_dir / "frame_%05d.jpg"

    # FFmpeg command: resample timeline to 1 frame every `sample_interval` seconds
    # using safe argument list (no shell injection)
    cmd = [
        "ffmpeg",
        "-v", "error",
        "-y",
        "-i", str(video_path),
        "-vf", f"fps=1/{sample_interval}",
        "-q:v", "2",
        str(output_pattern)
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_seconds,
            check=False
        )
    except subprocess.TimeoutExpired:
        raise FrameExtractionException("EXTRACTION_TIMEOUT", "Frame extraction exceeded timeout limit")
    except Exception as e:
        raise FrameExtractionException("EXTRACTION_ERROR", f"Subprocess error: {str(e)}")

    if result.returncode != 0:
        logger.error(f"ffmpeg frame extraction failed: {result.stderr.strip()}")
        raise FrameExtractionException("EXTRACTION_FAILED", "Failed to extract frames from media")

    # Collect extracted image files ordered by filename
    frame_files = sorted(temp_dir.glob("frame_*.jpg"))
    if not frame_files:
        raise FrameExtractionException("NO_FRAMES_EXTRACTED", "No frames were generated from video")

    extracted: List[ExtractedFrame] = []
    for idx, frame_path in enumerate(frame_files):
        # Monotonic timeline timestamp
        ts = round(idx * sample_interval, 3)
        # Cap to video duration if slightly exceeding due to rounding
        if ts > metadata.duration_seconds:
            ts = metadata.duration_seconds

        try:
            with Image.open(frame_path) as img:
                w, h = img.size
        except Exception:
            w, h = metadata.width, metadata.height

        extracted.append(
            ExtractedFrame(
                timestamp_seconds=ts,
                image_path=frame_path,
                width=w,
                height=h
            )
        )

    return extracted

