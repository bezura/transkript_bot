from transkript_bot.transcription.whisperx_cli import build_whisperx_cmd


def test_build_cmd():
    cmd = build_whisperx_cmd("in.wav", "out", "large-v2", "auto", False, None)
    assert "whisperx" in cmd[0]
