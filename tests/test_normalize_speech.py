import os
import shutil
import subprocess
import wave

import pytest

from tagwerk.contracts import validate
from tagwerk.pipeline import normalize, speech

SENTENCE = "Stuhlreihe A ist montiert. Zwei Mann vom Trockenbau sind heute krank. Die Traverse ist verkabelt."


def _capture(media, lang="de"):
    return {"capture_id": "cap-ns", "ts_device": "2026-11-26T09:12:00+01:00", "ts_server": "2026-11-26T08:12:03Z",
            "gps": None, "zone_id": "Z-STAGE", "lang": lang, "media": media, "note": None}


def test_zero_byte_video_does_not_raise(tmp_path):
    bad = tmp_path / "walk.mp4"
    bad.write_bytes(b"\x00" * 10)
    out = normalize.normalize(_capture([{"type": "video", "path": str(bad)}]), tmp_path / "work")
    assert out["audio"] is None and out["photos"] == [] and out["duration_s"] is None
    assert (tmp_path / "work" / "frames").is_dir()


def test_missing_file_is_skipped(tmp_path):
    out = normalize.normalize(_capture([{"type": "audio", "path": str(tmp_path / "nope.m4a")}]), tmp_path / "w")
    assert out["audio"] is None


def test_jpeg_photo_is_copied(tmp_path):
    jpg = tmp_path / "IMG_1.jpg"
    jpg.write_bytes(b"\xff\xd8\xff\xd9")
    out = normalize.normalize(_capture([{"type": "photo", "path": str(jpg)}]), tmp_path / "w")
    assert [p.rsplit("/", 1)[-1] for p in out["photos"]] == ["photo_IMG_1.jpg"]
    assert (tmp_path / "w" / "frames" / "photo_IMG_1.jpg").read_bytes() == jpg.read_bytes()


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_real_clip_gives_wav_and_frames(tmp_path):
    clip = tmp_path / "walk.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=1280x720:rate=10:duration=3",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=3", "-shortest", "-pix_fmt", "yuv420p",
                    str(clip)], check=True)
    out = normalize.normalize(_capture([{"type": "video", "path": str(clip)}]), tmp_path / "w")
    with wave.open(out["audio"]) as w:
        assert (w.getnchannels(), w.getframerate()) == (1, 16000)
    frames = sorted((tmp_path / "w" / "frames").glob("0*.jpg"))
    assert len(frames) in (3, 4) and frames[0].name == "0001.jpg"
    assert out["duration_s"] == pytest.approx(3, abs=0.2)


def test_speech_stub_when_no_audio(tmp_path):
    out = speech.transcribe(_capture([], lang="en"), {"audio": None})
    validate("transcript", out)
    assert out["capture_id"] == "cap-ns" and out["lang"] == "en"
    empty = tmp_path / "audio.wav"
    empty.write_bytes(b"")
    assert speech.transcribe(_capture([]), {"audio": str(empty)})["lang"] == "de"


def test_glossary_has_the_site_terms():
    text = speech._glossary()
    assert text and all(t in text for t in ("Stuhlreihe", "Traverse", "Trockenbauer", "krank", "verkabelt"))


@pytest.mark.gpu
@pytest.mark.skipif(os.environ.get("RUN_GPU_TESTS") != "1", reason="set RUN_GPU_TESTS=1 on the GPU machine")
def test_real_whisper_on_gpu(tmp_path):
    espeak = shutil.which("espeak-ng")
    if espeak is None:
        pytest.skip("espeak-ng not installed: cannot synthesise German speech")
    wav = tmp_path / "audio.wav"
    subprocess.run([espeak, "-v", "de", "-w", str(wav), SENTENCE], check=True)
    out = speech.transcribe(_capture([]), {"audio": str(wav)})
    validate("transcript", out)
    text = " ".join(s["text"] for s in out["segments"]).lower()
    assert "traverse" in text and out["lang"] == "de"
    assert all(0 <= s["start"] <= s["end"] for s in out["segments"])


def test_whisper_loads_from_local_cache_without_network(monkeypatch):
    """faster-whisper asks the HF hub for model info on every load; an unreachable hub hung the GPU worker for
    minutes. Load with local_files_only first and download only when the model is not cached."""
    import sys
    import types

    from tagwerk.pipeline import speech

    calls = []

    class FakeModel:
        def __init__(self, name, device, compute_type, local_files_only=False):
            calls.append(local_files_only)
            if not local_files_only and not cached:
                calls.append("downloaded")

    mod = types.ModuleType("faster_whisper")
    mod.WhisperModel = FakeModel
    monkeypatch.setitem(sys.modules, "faster_whisper", mod)
    monkeypatch.setattr(speech, "_models", {})
    cached = True
    speech._model()
    assert calls == [True]  # cached: never touched the network

    class NotCached(FakeModel):
        def __init__(self, name, device, compute_type, local_files_only=False):
            calls.append(local_files_only)
            if local_files_only:
                raise OSError("not in cache")

    mod.WhisperModel = NotCached
    monkeypatch.setattr(speech, "_models", {})
    calls.clear()
    speech._model()
    assert calls == [True, False]  # not cached: falls back to the normal (downloading) load


def test_whisper_load_narrow_fallback(monkeypatch):
    """Only a cache miss (OSError/ValueError) falls back to the downloading load; a CUDA RuntimeError must propagate
    instead of silently hitting the HF hub (the hang)."""
    import sys
    import types

    import pytest

    from tagwerk.pipeline import speech

    def fake(exc):
        class M:
            def __init__(self, name, device, compute_type, local_files_only=False):
                if local_files_only:
                    raise exc
        return M

    mod = types.ModuleType("faster_whisper")
    monkeypatch.setitem(sys.modules, "faster_whisper", mod)
    mod.WhisperModel = fake(RuntimeError("CUDA failed with error unknown"))
    monkeypatch.setattr(speech, "_models", {})
    with pytest.raises(RuntimeError):
        speech._model()
    mod.WhisperModel = fake(FileNotFoundError("not cached"))
    monkeypatch.setattr(speech, "_models", {})
    assert speech._model() is not None


def test_concat_line_escapes_apostrophes(tmp_path):
    from tagwerk.pipeline.normalize import concat_line

    p = tmp_path / "Peter's walk.wav"
    assert concat_line(p) == "file '" + str(p.resolve()).replace("'", "'\\''") + "'\n"
    assert "Peter'\\''s walk.wav'" in concat_line(p)
