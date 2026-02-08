from transkript_bot.services.progress import format_progress


def test_format_progress():
    text = format_progress(stage="transcribing", position=2, eta=120)
    assert "transcribing" in text
    assert "ETA" in text
