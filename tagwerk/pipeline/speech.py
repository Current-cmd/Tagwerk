"""Speech-to-text -> transcript contract.

TODO(feat/speech):
- faster-whisper; benchmark large-v3-turbo vs small; compute_type="int8" (never float16 on Pascal)
- vad_filter=True; language from capture["lang"] unless "auto"
- initial_prompt = German/English site glossary (seed/glossary.txt)
- segment start/end in seconds from the start of the media file
"""
from tagwerk.pipeline import stub


def transcribe(capture: dict, derived: dict) -> dict:
    return stub("transcript", capture["capture_id"])
