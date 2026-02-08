def choose_backend(*, force: str | None, has_gpu: bool) -> str:
    if force:
        return force
    return "whisperx" if has_gpu else "faster"
