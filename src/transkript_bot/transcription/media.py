from __future__ import annotations

import subprocess


def build_ffmpeg_cmd(input_path: str, output_path: str) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        output_path,
    ]


def convert_to_wav(input_path: str, output_path: str) -> None:
    cmd = build_ffmpeg_cmd(input_path, output_path)
    subprocess.run(cmd, check=True)
