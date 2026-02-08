from __future__ import annotations

from typing import Any


def normalize_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for seg in segments:
        item = dict(seg)
        item.setdefault("speaker", "SPEAKER_00")
        normalized.append(item)
    return normalized


def run_faster_whisper(
    wav_path: str,
    *,
    model_size: str,
    language: str,
    device: str,
    compute_type: str,
) -> list[dict[str, Any]]:
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments, _info = model.transcribe(wav_path, language=None if language == "auto" else language)
    result = [
        {"start": seg.start, "end": seg.end, "text": seg.text}
        for seg in segments
    ]
    return normalize_segments(result)
