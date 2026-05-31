from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Callable

ProgressCallback = Callable[[int, int], None]


def sha256_file(
    path: Path,
    chunk_size: int = 1024 * 1024,
    progress_callback: ProgressCallback | None = None,
) -> str:
    digest = hashlib.sha256()
    total_size = path.stat().st_size
    bytes_read = 0
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(chunk_size), b""):
            digest.update(chunk)
            bytes_read += len(chunk)
            if progress_callback is not None:
                progress_callback(bytes_read, total_size)
    return digest.hexdigest()
