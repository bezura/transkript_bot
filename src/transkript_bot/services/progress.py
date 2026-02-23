from __future__ import annotations


def _overall_percent(stage: str, transcribe_percent: int | None) -> int:
    if stage == "downloading":
        return 10
    if stage == "converting":
        return 30
    if stage == "transcribing":
        tp = 0 if transcribe_percent is None else max(0, min(100, transcribe_percent))
        return 30 + int(tp * 0.6)
    if stage == "uploading":
        return 95
    if stage == "done":
        return 100
    return 0


def format_progress(
    stage: str,
    position: int | None = None,
    eta: int | None = None,
    transcribe_percent: int | None = None,
) -> str:
    overall = _overall_percent(stage, transcribe_percent)
    lines = [f"Progress: {overall}%"]
    if position is not None:
        lines.append(f"Queue position: {position}")
    if eta is not None:
        if eta < 0:
            lines.append("ETA: unknown")
        else:
            lines.append(f"ETA: {eta} sec")
    labels = {
        "downloading": "Downloading...",
        "converting": "Converting...",
        "transcribing": "Transcribing...",
        "uploading": "Uploading...",
    }
    lines.append("")
    if stage == "transcribing" and transcribe_percent is not None:
        lines.append(f"Stage: Transcribing... {max(0, min(100, transcribe_percent))}%")
    elif stage in labels:
        lines.append(f"Stage: {labels[stage]}")
    if stage == "done":
        lines.append("")
        lines.append("Done. Choose output format:")
    return "\n".join(lines)
