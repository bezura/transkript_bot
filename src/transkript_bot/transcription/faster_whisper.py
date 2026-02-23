from __future__ import annotations

from typing import Any, Callable


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
    on_progress: Callable[[int], None] | None = None,
) -> list[dict[str, Any]]:
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments, info = model.transcribe(
        wav_path,
        language=None if language == "auto" else language,
        beam_size=1,
        best_of=1,
        condition_on_previous_text=False,
        vad_filter=True,
    )
    duration = float(getattr(info, "duration", 0.0) or 0.0)
    last_progress = -1
    result: list[dict[str, Any]] = []
    for seg in segments:
        result.append({"start": seg.start, "end": seg.end, "text": seg.text})
        if on_progress and duration > 0:
            current = max(1, min(99, int((float(seg.end) / duration) * 100)))
            if current > last_progress:
                last_progress = current
                on_progress(current)
    return normalize_segments(result)
