from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import PlanItem, Status, TransferResult


def default_manifest_path(destination: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return destination / "manifests" / f"inventory-sorter-{timestamp}.jsonl"


class ManifestWriter:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("a", encoding="utf-8")

    def write_plan(self, item: PlanItem) -> None:
        self._write(
            {
                "event": "plan",
                "status": Status.PLANNED.value,
                **serialize_plan_item(item),
            }
        )

    def write_result(self, result: TransferResult) -> None:
        self._write(
            {
                "event": "result",
                "status": result.status.value,
                "message": result.message,
                **serialize_plan_item(result.item),
            }
        )

    def close(self) -> None:
        self._file.close()

    def __enter__(self) -> "ManifestWriter":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def _write(self, data: dict[str, Any]) -> None:
        data["timestamp"] = datetime.now().isoformat(timespec="seconds")
        self._file.write(json.dumps(data, sort_keys=True) + "\n")
        self._file.flush()


def serialize_plan_item(item: PlanItem) -> dict[str, Any]:
    return {
        "action": item.action.value,
        "source": str(item.source),
        "destination": str(item.destination) if item.destination else None,
        "category": item.category,
        "sort_month": item.sort_month,
        "sha256": item.sha256,
        "duplicate_of": str(item.duplicate_of) if item.duplicate_of else None,
        "reason": item.reason,
    }

