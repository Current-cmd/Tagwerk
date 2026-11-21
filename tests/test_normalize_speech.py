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
    assert calls == [True, True, False]  # turbo not cached -> small not cached -> only small may be downloaded


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


def _write_wav(path, samples):
    import numpy as np

    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setframerate(16000)
        w.setsampwidth(2)
        w.writeframes((np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes())


def test_quiet_voice_is_levelled_before_whisper(tmp_path, monkeypatch):
    """A phone filming a venue records the speaker at ~-36 dB: the VAD then drops almost every sentence.
    Quiet audio (mean < QUIET_DB) is levelled (ffmpeg dynaudnorm) before Whisper; normal audio is untouched."""
    import numpy as np

    t = np.arange(16000 * 4) / 16000
    quiet = 0.01 * np.sin(2 * np.pi * 220 * t)  # about -43 dBFS
    loud = 0.3 * np.sin(2 * np.pi * 220 * t)  # about -13 dBFS
    assert speech.mean_db(quiet.astype(np.float32)) < speech.QUIET_DB < speech.mean_db(loud.astype(np.float32))
    seen = []

    class Fake:
        def transcribe(self, audio, **kw):
            seen.append(speech.mean_db(audio))
            return iter([]), type("I", (), {"language": "en"})()

    monkeypatch.setattr(speech, "_model", lambda: Fake())
    import sys
    import types

    monkeypatch.setitem(sys.modules, "faster_whisper", types.ModuleType("faster_whisper"))
    for name, sig in (("quiet.wav", quiet), ("loud.wav", loud)):
        _write_wav(tmp_path / name, sig)
        speech.transcribe({"capture_id": "c", "lang": "en"}, {"audio": str(tmp_path / name)})
    if shutil.which("ffmpeg"):
        assert seen[0] > speech.QUIET_DB  # levelled
    assert abs(seen[1] - speech.mean_db(loud.astype(np.float32))) < 0.5  # untouched


def test_segments_carry_word_timestamps_and_validate(tmp_path, monkeypatch):
    """Whisper can merge a long walk into one 90 s segment; the words keep the second each item is named."""
    import sys
    import types

    import numpy as np

    W = type("W", (), {})

    def word(s, e, w):
        x = W()
        x.start, x.end, x.word = s, e, w
        return x

    seg = type("S", (), {"start": 0.8, "end": 93.3, "text": " The tables over here.",
                         "words": [word(50.9, 51.2, " The"), word(51.2, 51.7, " tables"), word(51.7, 52.0, " over"),
                                   word(52.0, 52.4, " here.")]})()
    seen = {}

    class Fake:
        def transcribe(self, audio, **kw):
            seen.update(kw)
            return iter([seg]), type("I", (), {"language": "en"})()

    monkeypatch.setattr(speech, "_model", lambda: Fake())
    monkeypatch.setitem(sys.modules, "faster_whisper", types.ModuleType("faster_whisper"))
    _write_wav(tmp_path / "a.wav", 0.3 * np.sin(np.arange(16000) / 5))
    out = validate("transcript", speech.transcribe({"capture_id": "c", "lang": "en"}, {"audio": str(tmp_path / "a.wav")}))
    assert seen["word_timestamps"] is True
    # noisy venue audio: without it Whisper filled 30 s of near-silence with invented text and dropped the real
    # sentence in 1 of 6 runs (5/5 stable with it)
    assert seen["hallucination_silence_threshold"] == speech.HALLUCINATION_SILENCE_S
    assert out["segments"][0]["words"][1] == {"start": 51.2, "end": 51.7, "word": "tables"}



def _fake_whisper(monkeypatch, cached=("large-v3-turbo", "small"), cuda_oom=False):
    """Fake faster_whisper whose WhisperModel records (name, device, local_files_only); `cached` = models it can load
    offline, cuda_oom = every cuda load raises like a full GPU."""
    import sys
    import types

    from tagwerk.pipeline import speech

    calls = []

    class M:
        def __init__(self, name, device, compute_type, local_files_only=False):
            calls.append((name, device, local_files_only))
            assert compute_type == "int8"
            if device == "cuda" and cuda_oom:
                raise RuntimeError("CUDA failed with error out of memory")
            if local_files_only and name not in cached:
                raise OSError("not in cache")

    mod = types.ModuleType("faster_whisper")
    mod.WhisperModel = M
    monkeypatch.setitem(sys.modules, "faster_whisper", mod)
    monkeypatch.setattr(speech, "_models", {})
    monkeypatch.delenv("WHISPER_MODEL", raising=False)
    monkeypatch.delenv("WHISPER_DEVICE", raising=False)
    monkeypatch.setattr(speech, "_cuda_available", lambda: True)
    return calls


def test_default_model_is_large_v3_turbo_on_cpu_int8(monkeypatch):
    """Turbo fits next to YOLO + YOLO-World + RelateAnything only on the CPU (4.6 of 6 GB are taken on the GTX 1060)."""
    from tagwerk.pipeline import speech

    calls = _fake_whisper(monkeypatch)
    speech._model()
    assert calls == [("large-v3-turbo", "cpu", True)]


def test_env_overrides_model_and_device(monkeypatch):
    from tagwerk.pipeline import speech

    calls = _fake_whisper(monkeypatch)
    monkeypatch.setenv("WHISPER_MODEL", "small")
    monkeypatch.setenv("WHISPER_DEVICE", "cuda")
    speech._model()
    assert calls == [("small", "cuda", True)]
    calls = _fake_whisper(monkeypatch, cached=("/models/my-whisper",))
    monkeypatch.setenv("WHISPER_MODEL", "/models/my-whisper")  # a local path or full repo id passes through unchanged
    monkeypatch.setenv("WHISPER_DEVICE", "cpu")
    speech._model()
    assert calls == [("/models/my-whisper", "cpu", True)]


def test_turbo_not_cached_falls_back_to_small_without_downloading_turbo(monkeypatch, caplog):
    import logging

    from tagwerk.pipeline import speech

    calls = _fake_whisper(monkeypatch, cached=("small",))
    with caplog.at_level(logging.WARNING):
        speech._model()
    assert calls == [("large-v3-turbo", "cpu", True), ("small", "cuda", True)]  # no multi-GB download attempt
    assert "large-v3-turbo" in caplog.text and "small" in caplog.text


def test_gpu_out_of_memory_retries_the_same_model_on_cpu(monkeypatch):
    from tagwerk.pipeline import speech

    calls = _fake_whisper(monkeypatch, cuda_oom=True)
    monkeypatch.setenv("WHISPER_DEVICE", "cuda")
    speech._model()
    assert calls == [("large-v3-turbo", "cuda", True), ("large-v3-turbo", "cpu", True)]


def test_worker_warms_the_models_at_startup(monkeypatch):
    from tagwerk import worker_api
    from tagwerk.pipeline import speech, vision

    seen = []
    monkeypatch.setattr(speech, "_model", lambda: seen.append("whisper"))
    monkeypatch.setattr(vision, "ml_available", lambda: True)
    monkeypatch.setattr(vision, "models", lambda: seen.append("vision"))
    worker_api.warm_models()
    assert seen == ["vision", "whisper"]  # vision first: whisper goes where the GPU memory is left
    monkeypatch.setenv("TAGWERK_NO_WARMUP", "1")
    seen.clear()
    worker_api.warm_models()
    assert seen == []
