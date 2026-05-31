from __future__ import annotations

import os
from pathlib import Path

from .hashutil import sha256_file
from .models import Action, PlanItem, Status, TransferResult

COPY_CHUNK_SIZE = 1024 * 1024


def apply_plan_item(item: PlanItem, verbose: bool = False) -> TransferResult:
    try:
        if item.action == Action.COPY_AND_DELETE_SOURCE:
            if item.destination is None or item.sha256 is None:
                raise ValueError("Copy action is missing destination or hash.")
            safe_copy_verify_delete(item.source, item.destination, item.sha256)
            message = f"copied and removed source: {item.source}"
            if verbose:
                print(message)
            return TransferResult(item=item, status=Status.DONE, message=message)

        if item.action == Action.DELETE_DUPLICATE_SOURCE:
            item.source.unlink()
            message = f"removed duplicate source: {item.source}"
            if verbose:
                print(message)
            return TransferResult(item=item, status=Status.DONE, message=message)

        if item.action == Action.SKIP_DUPLICATE:
            return TransferResult(item=item, status=Status.SKIPPED, message=item.reason)

        return TransferResult(item=item, status=Status.ERROR, message=item.reason)
    except Exception as exc:
        return TransferResult(item=item, status=Status.ERROR, message=str(exc))


def safe_copy_verify_delete(source: Path, destination: Path, expected_sha256: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_destination = temp_path_for(destination)

    if temp_destination.exists():
        temp_destination.unlink()

    try:
        copy_file_bytes(source, temp_destination)

        source_size = source.stat().st_size
        temp_size = temp_destination.stat().st_size
        if source_size != temp_size:
            raise IOError(
                f"copy size mismatch for {source}: source={source_size}, copy={temp_size}"
            )

        copied_sha256 = sha256_file(temp_destination)
        if copied_sha256 != expected_sha256:
            raise IOError(f"copy hash mismatch for {source}")

        if destination.exists():
            raise FileExistsError(f"destination already exists: {destination}")

        os.replace(temp_destination, destination)
        source.unlink()
    except Exception:
        if temp_destination.exists():
            temp_destination.unlink()
        raise


def temp_path_for(destination: Path) -> Path:
    return destination.with_name(f".{destination.name}.part")


def copy_file_bytes(source: Path, destination: Path) -> None:
    with source.open("rb") as source_file:
        with destination.open("wb") as destination_file:
            for chunk in iter(lambda: source_file.read(COPY_CHUNK_SIZE), b""):
                destination_file.write(chunk)
            destination_file.flush()
            try:
                os.fsync(destination_file.fileno())
            except OSError:
                # Some virtual/network filesystems, including GVFS SMB mounts,
                # do not support fsync. The caller still verifies the closed
                # destination file by size and SHA-256 before removing source.
                pass
