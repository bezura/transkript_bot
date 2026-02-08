from __future__ import annotations


def format_progress(stage: str, position: int | None = None, eta: int | None = None) -> str:
    lines = [f"Stage: {stage}"]
    if position is not None:
        lines.append(f"Queue position: {position}")
    if eta is not None:
        if eta < 0:
            lines.append("ETA: unknown")
        else:
            lines.append(f"ETA: {eta} sec")
    return "\n".join(lines)
