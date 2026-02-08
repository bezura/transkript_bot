from transkript_bot.transcription.media import build_ffmpeg_cmd


def test_build_ffmpeg_cmd():
    cmd = build_ffmpeg_cmd("in.mp4", "out.wav")
    assert cmd[:2] == ["ffmpeg", "-y"]
