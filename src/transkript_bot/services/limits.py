from __future__ import annotations

MAX_CLOUD_FILE_SIZE = 20 * 1024 * 1024


def is_cloud_file_too_large(size_bytes: int | None) -> bool:
    if size_bytes is None:
        return False
    return size_bytes > MAX_CLOUD_FILE_SIZE
