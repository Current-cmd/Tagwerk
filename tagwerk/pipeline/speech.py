"""Speech-to-text -> transcript contract.

faster-whisper with int8 (never float16: Pascal has no fast fp16), VAD on, language from
capture["lang"] unless "auto", and the German/English site glossary as initial prompt.
Segment start/end are seconds from the start of the media file.

Falls back to the fixture stub (with `lang` set) when faster-whisper is not installed or there is
no audio, which keeps the CPU-only Mac tests green.
"""
import logging
import os
import wave
from pathlib import Path

from tagwerk.pipeline import stub

log = logging.getLogger(__name__)

GLOSSARY = Path(__file__).resolve().parents[2] / "seed" / "glossary.txt"
_models: dict[tuple[str, str], object] = {}


def _glossary() -> str | None:
    try:
        text = " ".join(GLOSSARY.read_text(encoding="utf-8").split())
    except OSError:
        return None
    return text or None


def _device() -> str:
    try:
        import ctranslate2

        return "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
    except Exception:  # noqa: BLE001 - any failure means CPU
        return "cpu"


def _model():
    """Lazy module-level singleton per (model name, device)."""
    from faster_whisper import WhisperModel

    key = (os.environ.get("WHISPER_MODEL", "small"), _device())
    if key not in _models:
        log.info("loading whisper %s on %s (int8)", *key)
        _models[key] = WhisperModel(key[0], device=key[1], compute_type="int8")
    return _models[key]


def _load_wav(path: str):
    """Our own normalized WAV (16 kHz mono s16) as float32. Read directly so faster-whisper never calls PyAV
    (faster-whisper 1.2.1 passes `metadata_errors` to av.open, which av 19.x rejects)."""
    import numpy as np

    with wave.open(path, "rb") as w:
        assert (w.getnchannels(), w.getframerate(), w.getsampwidth()) == (1, 16000, 2), "expected 16 kHz mono s16"
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0


def _has_audio(derived: dict) -> bool:
    path = derived.get("audio")
    return bool(path) and Path(path).is_file() and Path(path).stat().st_size > 44  # > bare WAV header


def transcribe(capture: dict, derived: dict) -> dict:
    lang = capture.get("lang", "auto")
    try:
        import faster_whisper  # noqa: F401
        available = True
    except ImportError:
        available = False
    if not available or not _has_audio(derived):
        out = stub("transcript", capture["capture_id"])
        if lang != "auto":
            out["lang"] = lang
        return out

    segments, info = _model().transcribe(
        _load_wav(derived["audio"]),
        language=None if lang == "auto" else lang,
        vad_filter=True,
        initial_prompt=_glossary(),
    )
    return {
        "capture_id": capture["capture_id"],
        "lang": info.language,
        "segments": [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()}
                     for s in segments],
    }
