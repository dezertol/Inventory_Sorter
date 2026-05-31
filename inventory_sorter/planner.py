from __future__ import annotations

from pathlib import Path

from .classifier import classify
from .dates import best_sort_date
from .hashutil import sha256_file
from .index import DestinationIndex
from .models import Action, FileRecord, PlanItem


def build_plan(
    source_files: list[Path],
    destination: Path,
    destination_index: DestinationIndex,
    remove_duplicates: bool,
    verbose: bool = False,
) -> list[PlanItem]:
    plan: list[PlanItem] = []
    reserved_destinations: set[Path] = set()

    total = len(source_files)
    for index, source in enumerate(source_files, start=1):
        try:
            if verbose:
                print(f"planning [{index}/{total}]: {source}", flush=True)
            record = make_file_record(source)
            duplicate_of = destination_index.find_duplicate(
                source,
                record.sha256,
                record.size,
            )
            if duplicate_of is not None:
                action = (
                    Action.DELETE_DUPLICATE_SOURCE
                    if remove_duplicates
                    else Action.SKIP_DUPLICATE
                )
                item = PlanItem(
                    action=action,
                    source=source,
                    destination=None,
                    category=record.category,
                    sort_month=record.sort_date.strftime("%Y-%m"),
                    sha256=record.sha256,
                    duplicate_of=duplicate_of,
                    reason="duplicate content already exists in destination",
                )
            else:
                month = record.sort_date.strftime("%Y-%m")
                destination_dir = destination / record.category / month
                final_path = unique_destination(
                    destination_dir / source.name,
                    reserved_destinations,
                )
                reserved_destinations.add(final_path)
                item = PlanItem(
                    action=Action.COPY_AND_DELETE_SOURCE,
                    source=source,
                    destination=final_path,
                    category=record.category,
                    sort_month=month,
                    sha256=record.sha256,
                )
            plan.append(item)
        except Exception as exc:
            plan.append(
                PlanItem(
                    action=Action.SKIP_ERROR,
                    source=source,
                    destination=None,
                    category="Other",
                    sort_month="unknown",
                    reason=str(exc),
                )
            )

    return plan


def make_file_record(path: Path) -> FileRecord:
    stat = path.stat()
    sort_date = best_sort_date(path)
    return FileRecord(
        path=path,
        size=stat.st_size,
        suffix=path.suffix.lower(),
        category=classify(path),
        sort_date=sort_date,
        sha256=sha256_file(path),
    )


def unique_destination(path: Path, reserved: set[Path]) -> Path:
    candidate = path
    counter = 1
    while candidate.exists() or candidate in reserved:
        candidate = path.with_name(f"{path.stem} ({counter}){path.suffix}")
        counter += 1
    return candidate


def format_plan_item(item: PlanItem) -> str:
    if item.action == Action.COPY_AND_DELETE_SOURCE:
        return f"{item.action.value}: {item.source} -> {item.destination}"
    if item.duplicate_of:
        return f"{item.action.value}: {item.source} duplicates {item.duplicate_of}"
    return f"{item.action.value}: {item.source} ({item.reason})"
