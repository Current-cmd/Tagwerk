"""Speech-to-text -> transcript contract.

faster-whisper with int8 (never float16: Pascal has no fast fp16), VAD on, language from
capture["lang"] unless "auto", and the German/English site glossary as initial prompt.
Segment start/end are seconds from the start of the media file.

Falls back to the fixture stub (with `lang` set) when faster-whisper is not installed or there is
no audio, which keeps the CPU-only Mac tests green.
"""
import logging
import os
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np

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
        try:  # the cache first: a plain load asks the HF hub for model info and hangs when the hub is unreachable
            _models[key] = WhisperModel(key[0], device=key[1], compute_type="int8", local_files_only=True)
        except (OSError, ValueError):  # not cached yet: download once (CUDA/runtime errors must propagate)
            _models[key] = WhisperModel(key[0], device=key[1], compute_type="int8")
    return _models[key]


def _load_wav(path: str):
    """Our own normalized WAV (16 kHz mono s16) as float32. Read directly so faster-whisper never calls PyAV
    (faster-whisper 1.2.1 passes `metadata_errors` to av.open, which av 19.x rejects)."""
    import numpy as np

    with wave.open(path, "rb") as w:
        assert (w.getnchannels(), w.getframerate(), w.getsampwidth()) == (1, 16000, 2), "expected 16 kHz mono s16"
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0


HALLUCINATION_SILENCE_S = 2.0  # skip silent gaps > 2 s where Whisper starts inventing text (needs word timestamps)
QUIET_DB = -32.0  # mean level below which the voice is levelled first (venue walkthroughs: ~-36 dB; user_walk -28 dB)


def mean_db(samples: np.ndarray) -> float:
    """Mean level in dBFS (RMS), as ffmpeg volumedetect reports it."""
    rms = float(np.sqrt(np.mean(np.square(samples, dtype=np.float64)))) if len(samples) else 0.0
    return 20 * np.log10(rms) if rms > 0 else -120.0


def _levelled(path: str) -> np.ndarray:
    """The WAV, levelled with ffmpeg dynaudnorm when it is quiet (else, or without ffmpeg, as it is). Silero VAD drops
    a voice that sits at -36 dB under venue noise; after levelling Whisper gets the sentences."""
    audio = _load_wav(path)
    if mean_db(audio) >= QUIET_DB or not shutil.which("ffmpeg"):
        return audio
    out = Path(path).with_name(Path(path).stem + "_levelled.wav")
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path, "-af", "highpass=f=100,dynaudnorm=f=150:g=15",
                        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(out)], capture_output=True, timeout=120)
    if r.returncode != 0 or not out.exists():
        log.warning("levelling quiet audio failed: %s", r.stderr[-300:])
        return audio
    log.info("quiet audio (%.1f dB) levelled before transcription", mean_db(audio))
    return _load_wav(str(out))


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
    if not available:
        if os.environ.get("TAGWERK_STUBS") != "1":  # never pass fixture text off as real speech
            log.error("faster-whisper is not installed: speech stage returns no segments (install .[gpu])")
            return {"capture_id": capture["capture_id"], "lang": lang if lang != "auto" else "de", "segments": []}
        out = stub("transcript", capture["capture_id"])
        if lang != "auto":
            out["lang"] = lang
        return out
    if not _has_audio(derived):  # photo-only capture: nothing was said
        return {"capture_id": capture["capture_id"], "lang": lang if lang != "auto" else "de", "segments": []}

    segments, info = _model().transcribe(
        _levelled(derived["audio"]),
        language=None if lang == "auto" else lang,
        vad_filter=True,
        initial_prompt=_glossary(),
        word_timestamps=True,  # a long walk can come back as one 90 s segment: words keep each item's second
        hallucination_silence_threshold=HALLUCINATION_SILENCE_S,
    )
    return {
        "capture_id": capture["capture_id"],
        "lang": info.language,
        "segments": [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip(),
                      "words": [{"start": round(w.start, 2), "end": round(w.end, 2), "word": w.word.strip()}
                                for w in (getattr(s, "words", None) or [])]}
                     for s in segments],
    }
