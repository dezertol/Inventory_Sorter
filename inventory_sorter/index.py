from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .hashutil import sha256_file


@dataclass
class DestinationIndex:
    by_size: dict[int, list[Path]] = field(default_factory=lambda: defaultdict(list))
    by_hash: dict[str, Path] = field(default_factory=dict)

    def find_duplicate(self, path: Path, sha256: str, size: int) -> Path | None:
        if not self.by_size.get(size):
            return None
        return self.by_hash.get(sha256)

    def add(self, path: Path, sha256: str, size: int) -> None:
        self.by_size.setdefault(size, []).append(path)
        self.by_hash.setdefault(sha256, path)


def build_destination_index(destination: Path, verbose: bool = False) -> DestinationIndex:
    index = DestinationIndex()
    if not destination.exists():
        print("destination does not exist yet; duplicate index is empty", flush=True)
        return index

    manifest_dir = (destination / "manifests").resolve()
    count = 0
    for path in destination.rglob("*"):
        if not path.is_file():
            continue
        if _is_relative_to(path.resolve(), manifest_dir):
            continue
        if path.name.endswith(".part"):
            continue
        size = path.stat().st_size
        digest = sha256_file(path)
        index.add(path, digest, size)
        count += 1
        if verbose:
            print(f"indexed {path}")
        elif count % 100 == 0:
            print(f"indexed {count} destination files...", flush=True)

    print(f"indexed {count} destination files", flush=True)
    return index


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
