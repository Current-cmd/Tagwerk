"""FFmpeg normalization: 16 kHz mono WAV for Whisper, 1 frame/s at 960 px for vision, HEIC -> JPEG.

TODO(feat/ingest):
- ffmpeg -i <video> -ac 1 -ar 16000 audio.wav
- ffmpeg -i <video> -vf fps=1,scale=960:-2 frames/%04d.jpg   (frame t = index - 1 seconds)
- photos: keep EXIF time; convert HEIC with pillow-heif
"""
import shutil
from pathlib import Path


def normalize(capture: dict, workdir: Path) -> dict:
    """Return paths of derived media. Stub: reports what would be produced."""
    workdir.mkdir(parents=True, exist_ok=True)
    return {
        "audio": str(workdir / "audio.wav"),
        "frames_dir": str(workdir / "frames"),
        "ffmpeg_available": shutil.which("ffmpeg") is not None,
    }
