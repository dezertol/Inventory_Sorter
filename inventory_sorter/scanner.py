from __future__ import annotations

from pathlib import Path


def scan_files(source: Path, destination: Path, include_hidden: bool = False) -> list[Path]:
    source = source.resolve()
    destination = destination.resolve()
    files: list[Path] = []

    for path in source.rglob("*"):
        if not path.is_file():
            continue
        if not include_hidden and _has_hidden_part(path.relative_to(source)):
            continue
        if _is_relative_to(path.resolve(), destination):
            continue
        files.append(path)

    return files


def validate_source_destination(source: Path, destination: Path) -> tuple[Path, Path]:
    source = source.expanduser().resolve()
    destination = destination.expanduser().resolve()

    if not source.exists():
        raise ValueError(f"Source does not exist: {source}")
    if not source.is_dir():
        raise ValueError(f"Source is not a directory: {source}")
    if source == destination:
        raise ValueError("Source and destination must be different directories.")
    if _is_relative_to(destination, source):
        raise ValueError("Destination cannot be inside the source tree.")
    if _is_relative_to(source, destination):
        raise ValueError("Source cannot be inside the destination tree.")

    return source, destination


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _has_hidden_part(path: Path) -> bool:
    return any(part.startswith(".") for part in path.parts)

