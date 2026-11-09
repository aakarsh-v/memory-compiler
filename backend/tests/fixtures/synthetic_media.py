import subprocess
from pathlib import Path


def create_synthetic_video(output_path: Path, duration_seconds: int = 5, width: int = 320, height: int = 240) -> Path:
    """
    Generates a deterministic synthetic MP4 video with a test pattern and audio tone
    using ffmpeg lavfi testsrc. Takes <0.5s and requires no external downloads.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-v", "error",
        "-y",
        "-f", "lavfi",
        "-i", f"testsrc=duration={duration_seconds}:size={width}x{height}:rate=30",
        "-f", "lavfi",
        "-i", f"sine=frequency=1000:duration={duration_seconds}",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        str(output_path)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_path

