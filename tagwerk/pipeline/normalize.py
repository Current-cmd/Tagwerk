"""FFmpeg normalization: 16 kHz mono WAV for Whisper, 1 frame/s at 960 px for vision, HEIC -> JPEG.

Never raises on bad input: a missing ffmpeg, a missing file or an undecodable file (tests upload
10 zero bytes) is logged as a warning and the stage returns whatever it could produce.

Frames are numbered continuously across videos (frame t = index - 1 seconds from the start of the
first video); photos keep their EXIF because JPEGs are copied byte for byte.
"""
import json
import logging
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

_JPEG = {".jpg", ".jpeg"}



def concat_line(path: Path) -> str:
    """One ffmpeg concat-demuxer line; a ' inside the path is closed, escaped and reopened ('\\'')."""
    return "file '" + str(path.resolve()).replace("'", "'\\''") + "'\n"

def _run(cmd: list[str]) -> bool:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("%s failed to run: %s", cmd[0], exc)
        return False
    if r.returncode != 0:
        log.warning("%s exited %s for %s: %s", cmd[0], r.returncode, cmd[-1], r.stderr.strip()[-300:])
        return False
    return True


def _probe(path: Path) -> dict | None:
    """ffprobe -> {"has_audio": bool, "duration": float | None}, or None if the file is not decodable."""
    if shutil.which("ffprobe") is None:
        return None
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
             "-of", "json", str(path)],
            capture_output=True, text=True, timeout=60)
        info = json.loads(r.stdout or "{}")
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        log.warning("ffprobe failed for %s: %s", path, exc)
        return None
    if r.returncode != 0 or "format" not in info:
        return None
    try:
        duration = float(info["format"]["duration"])
    except (KeyError, TypeError, ValueError):
        duration = None
    return {"has_audio": any(s.get("codec_type") == "audio" for s in info.get("streams", [])),
            "duration": duration}


def _photo(src: Path, frames: Path) -> Path | None:
    dest = frames / f"photo_{src.stem}.jpg"
    try:
        if src.suffix.lower() in _JPEG:
            shutil.copyfile(src, dest)  # byte copy keeps EXIF
            return dest
        if src.suffix.lower() in {".heic", ".heif"}:
            try:
                import pillow_heif
            except ImportError:
                log.warning("pillow-heif not installed, skipping %s", src.name)
                return None
            pillow_heif.register_heif_opener()
        from PIL import Image

        with Image.open(src) as im:
            exif = im.info.get("exif")
            im = im.convert("RGB")
            im.save(dest, "JPEG", quality=92, **({"exif": exif} if exif else {}))
        return dest
    except Exception as exc:  # noqa: BLE001 - one bad photo must not stop the capture
        log.warning("could not convert photo %s: %s", src.name, exc)
        return None


def _frames(src: Path, frames: Path, first_index: int) -> int:
    """Extract 1 fps / 960 px JPEGs from `src`, numbered from first_index. Returns how many were written."""
    tmp = frames / f"_tmp_{first_index:04d}"
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        if not _run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", "fps=1,scale=960:-2",
                     str(tmp / "%04d.jpg")]):
            return 0
        n = 0
        for n, jpg in enumerate(sorted(tmp.glob("*.jpg")), start=1):
            jpg.rename(frames / f"{first_index + n - 1:04d}.jpg")
        return n
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def normalize(capture: dict, workdir: Path) -> dict:
    """Return paths of derived media; see module docstring for the never-raise policy."""
    workdir = Path(workdir)
    frames = workdir / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    have_ffmpeg = shutil.which("ffmpeg") is not None
    if not have_ffmpeg:
        log.warning("ffmpeg not found: no audio or video frames will be produced")

    wavs: list[Path] = []
    photos: list[str] = []
    durations: list[float] = []
    next_frame = 1

    for i, m in enumerate(capture.get("media", [])):
        src = Path(m["path"])
        if not src.exists():
            log.warning("media file missing: %s", src)
            continue
        if m["type"] == "photo":
            if (p := _photo(src, frames)) is not None:
                photos.append(str(p))
            continue
        if not have_ffmpeg:
            continue
        info = _probe(src)
        if info is None:
            log.warning("not decodable, skipping: %s", src)
            continue
        if info["duration"] is not None:
            durations.append(info["duration"])
        if info["has_audio"]:
            wav = workdir / f"_audio_{i}.wav"
            if _run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", str(wav)]):
                wavs.append(wav)
        else:
            log.info("no audio stream in %s", src.name)
        if m["type"] == "video":
            next_frame += _frames(src, frames, next_frame)

    audio = workdir / "audio.wav"
    if len(wavs) == 1:
        wavs[0].replace(audio)
    elif wavs:
        listing = workdir / "_concat.txt"
        listing.write_text("".join(concat_line(w) for w in wavs))
        ok = _run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(listing),
                   "-c", "copy", str(audio)])
        listing.unlink(missing_ok=True)
        if not ok:
            audio.unlink(missing_ok=True)
    for w in wavs:
        w.unlink(missing_ok=True)

    return {
        "audio": str(audio) if audio.exists() else None,
        "frames_dir": str(frames),
        "photos": photos,
        "duration_s": round(sum(durations), 3) if durations else None,
        "ffmpeg_available": have_ffmpeg,
    }
