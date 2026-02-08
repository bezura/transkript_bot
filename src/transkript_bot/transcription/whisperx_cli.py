from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def build_whisperx_cmd(
    wav_path: str,
    out_dir: str,
    model: str,
    language: str,
    diarize: bool,
    hf_token: str | None,
    whisperx_cmd: str = "whisperx",
) -> list[str]:
    cmd = [
        whisperx_cmd,
        wav_path,
        "--model",
        model,
        "--output_dir",
        out_dir,
        "--output_format",
        "json",
        "--language",
        language,
        "--vad_method",
        "silero",
    ]
    if diarize and hf_token:
        cmd += ["--diarize", "--hf_token", hf_token]
    return cmd


def run_whisperx(
    wav_path: str,
    out_dir: str,
    *,
    model: str,
    language: str,
    diarize: bool,
    hf_token: str | None,
    whisperx_cmd: str = "whisperx",
) -> list[dict[str, Any]]:
    cmd = build_whisperx_cmd(
        wav_path,
        out_dir,
        model,
        language,
        diarize,
        hf_token,
        whisperx_cmd=whisperx_cmd,
    )
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(
            proc.returncode, cmd, output=proc.stdout, stderr=proc.stderr
        )
    json_files = sorted(Path(out_dir).glob("*.json"))
    if not json_files:
        raise FileNotFoundError("WhisperX did not produce JSON output")
    data = json.loads(json_files[-1].read_text(encoding="utf-8"))
    return data.get("segments", [])
