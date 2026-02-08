def estimate_eta(durations: list[int], position: int) -> int:
    if position <= 1:
        return 0
    if not durations:
        return -1
    avg = sum(durations) // len(durations)
    return avg * (position - 1)
