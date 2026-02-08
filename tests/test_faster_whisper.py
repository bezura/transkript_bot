from transkript_bot.transcription.faster_whisper import normalize_segments


def test_normalize_segments():
    segs = [{"start": 0.0, "end": 1.0, "text": "ok"}]
    out = normalize_segments(segs)
    assert out[0]["speaker"] == "SPEAKER_00"
