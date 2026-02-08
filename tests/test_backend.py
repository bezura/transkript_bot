from transkript_bot.transcription.backend import choose_backend


def test_choose_backend_force():
    assert choose_backend(force="whisperx", has_gpu=False) == "whisperx"
