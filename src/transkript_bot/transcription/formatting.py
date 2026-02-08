def sec_to_hms(sec: float) -> str:
    m = int(sec // 60)
    s = sec % 60
    return f"{m:02d}:{s:06.3f}"


def segments_to_txt(segments: list[dict]) -> str:
    lines = []
    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        start = sec_to_hms(float(seg.get("start", 0.0)))
        end = sec_to_hms(float(seg.get("end", 0.0)))
        speaker = seg.get("speaker", "SPEAKER")
        lines.append(f"[{start} – {end}] {speaker}:")
        lines.append(text)
        lines.append("")
    return "\n".join(lines).strip() + "\n"
