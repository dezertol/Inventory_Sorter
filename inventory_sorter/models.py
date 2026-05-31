from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path


class Action(str, Enum):
    COPY_AND_DELETE_SOURCE = "COPY_AND_DELETE_SOURCE"
    DELETE_DUPLICATE_SOURCE = "DELETE_DUPLICATE_SOURCE"
    SKIP_DUPLICATE = "SKIP_DUPLICATE"
    SKIP_ERROR = "SKIP_ERROR"


class Status(str, Enum):
    PLANNED = "PLANNED"
    DONE = "DONE"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


@dataclass(frozen=True)
class FileRecord:
    path: Path
    size: int
    suffix: str
    category: str
    sort_date: datetime
    sha256: str


@dataclass(frozen=True)
class PlanItem:
    action: Action
    source: Path
    destination: Path | None
    category: str
    sort_month: str
    sha256: str | None = None
    duplicate_of: Path | None = None
    reason: str | None = None


@dataclass(frozen=True)
class TransferResult:
    item: PlanItem
    status: Status
    message: str | None = None

