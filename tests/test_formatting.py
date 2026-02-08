from transkript_bot.transcription.formatting import segments_to_txt


def test_segments_to_txt():
    segments = [{"start": 0.0, "end": 1.23, "speaker": "SPEAKER_00", "text": "Привет"}]
    out = segments_to_txt(segments)
    assert "SPEAKER_00" in out
    assert "Привет" in out
