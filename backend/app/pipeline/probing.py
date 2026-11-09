import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.core.errors import AppException
from app.core.logging import logger


class MediaProbeException(AppException):
    def __init__(self, code: str, message: str):
        super().__init__(code=code, message=message, status_code=400)


@dataclass
class VideoMetadata:
    duration_seconds: float
    width: int
    height: int
    fps: float
    has_audio: bool
    codec_name: str


def probe_video(video_path: Path, timeout_seconds: int = 30) -> VideoMetadata:
    """
    Safely probes media file using ffprobe with argument list (never shell strings).
    Extracts duration, dimensions, framerate, codec, and audio stream presence.
    """
    if not video_path.exists():
        raise MediaProbeException("MEDIA_FILE_NOT_FOUND", "Media file does not exist")

    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration:stream=width,height,r_frame_rate,codec_name,codec_type",
        "-of", "json",
        str(video_path)
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
        raise MediaProbeException("MEDIA_PROBE_TIMEOUT", "Probing media exceeded time limit")
    except Exception as e:
        raise MediaProbeException("MEDIA_PROBE_ERROR", f"Failed to execute media probe: {str(e)}")

    if result.returncode != 0:
        logger.warning(f"ffprobe failed with code {result.returncode}: {result.stderr.strip()}")
        raise MediaProbeException("MEDIA_CORRUPT", "Uploaded file could not be parsed as valid media")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise MediaProbeException("MEDIA_CORRUPT", "Malformed metadata from media probe")

    streams = data.get("streams", [])
    format_info = data.get("format", {})

    video_stream = None
    has_audio = False

    for s in streams:
        if s.get("codec_type") == "video" and not video_stream:
            video_stream = s
        elif s.get("codec_type") == "audio":
            has_audio = True

    if not video_stream:
        raise MediaProbeException("MEDIA_NO_VIDEO_STREAM", "No valid video stream found in media file")

    # Parse duration from format or stream
    raw_duration = format_info.get("duration") or video_stream.get("duration")
    if not raw_duration:
        raise MediaProbeException("MEDIA_INVALID_DURATION", "Unable to determine media duration")

    try:
        duration_seconds = float(raw_duration)
    except ValueError:
        raise MediaProbeException("MEDIA_INVALID_DURATION", "Invalid duration value in media metadata")

    width = video_stream.get("width")
    height = video_stream.get("height")
    codec_name = video_stream.get("codec_name", "unknown")

    if not width or not height:
        raise MediaProbeException("MEDIA_INVALID_DIMENSIONS", "Missing video dimensions")

    # Frame rate calculation (e.g. '30/1' or '24000/1001')
    r_fps = video_stream.get("r_frame_rate", "30/1")
    try:
        if "/" in r_fps:
            num, den = r_fps.split("/")
            fps = round(float(num) / float(den), 2) if float(den) != 0 else 30.0
        else:
            fps = round(float(r_fps), 2)
    except Exception:
        fps = 30.0

    return VideoMetadata(
        duration_seconds=round(duration_seconds, 3),
        width=int(width),
        height=int(height),
        fps=fps,
        has_audio=has_audio,
        codec_name=codec_name
    )

