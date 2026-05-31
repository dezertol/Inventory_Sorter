from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from time import monotonic

from .index import build_destination_index
from .manifest import ManifestWriter, default_manifest_path
from .models import Action, Status, TransferResult
from .planner import build_plan, format_plan_item
from .scanner import scan_files, validate_source_destination
from .transfer import apply_plan_item

LONG_FILE_PROGRESS_DELAY_SECONDS = 10.0
LONG_FILE_PROGRESS_INTERVAL_SECONDS = 1.0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "scan":
        return scan_command(args)

    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inventory-sorter",
        description="Safely organize files into a dated destination library.",
    )
    subparsers = parser.add_subparsers(dest="command")

    scan = subparsers.add_parser("scan", help="scan and organize a source directory")
    scan.add_argument("source", type=Path, help="source directory to scan recursively")
    scan.add_argument(
        "--destination",
        required=True,
        type=Path,
        help="separate sorted-library destination directory",
    )
    mode = scan.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--preview",
        action="store_true",
        help="show planned actions without changing files",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="copy, verify, and remove source files",
    )
    scan.add_argument(
        "--remove-duplicates",
        action="store_true",
        help="when applying, delete source files that already exist in destination",
    )
    scan.add_argument(
        "--include-hidden",
        action="store_true",
        help="include hidden files and directories in the source scan",
    )
    scan.add_argument(
        "--manifest-file",
        type=Path,
        help="write run audit records to this JSONL file",
    )
    scan.add_argument(
        "--verbose",
        action="store_true",
        help="print indexing, planning, and transfer details",
    )
    return parser


def scan_command(args: argparse.Namespace) -> int:
    try:
        source, destination = validate_source_destination(args.source, args.destination)
    except ValueError as exc:
        print(f"error: {exc}")
        return 2

    if args.remove_duplicates and not args.apply:
        print("error: --remove-duplicates can only be used with --apply")
        return 2

    print(f"source: {source}", flush=True)
    print(f"destination: {destination}", flush=True)
    print("building destination duplicate index...", flush=True)
    destination_index = build_destination_index(destination, verbose=args.verbose)

    print("scanning source tree...", flush=True)
    source_files = scan_files(source, destination, include_hidden=args.include_hidden)

    print(f"found {len(source_files)} source files", flush=True)
    print("building plan; hashing source files for duplicate checks...", flush=True)
    plan = build_plan(
        source_files,
        destination,
        destination_index,
        remove_duplicates=args.remove_duplicates,
        verbose=args.verbose,
    )

    print_summary(plan, preview=args.preview)

    manifest_path = args.manifest_file or default_manifest_path(destination)
    if args.preview:
        for item in plan:
            print(format_plan_item(item))
        print(f"preview only; no files changed. Manifest not written: {manifest_path}")
        return 0

    results: list[TransferResult] = []
    with ManifestWriter(manifest_path) as manifest:
        total = len(plan)
        started = monotonic()
        for index, item in enumerate(plan, start=1):
            print_progress(index, total, item, started)
            manifest.write_plan(item)
            reporter = LongFileProgressReporter()
            result = apply_plan_item(
                item,
                verbose=args.verbose,
                progress_callback=reporter.update,
            )
            reporter.finish()
            manifest.write_result(result)
            results.append(result)
            if result.status == Status.ERROR:
                print(f"  error: {result.message}", flush=True)

    print_result_summary(results, manifest_path)
    return 0 if all(result.status != Status.ERROR for result in results) else 1


def print_summary(plan: list, preview: bool) -> None:
    action_counts = Counter(item.action for item in plan)
    category_counts = Counter(item.category for item in plan)

    mode = "Preview" if preview else "Apply"
    print(f"{mode} summary")
    print(f"  planned files: {len(plan)}")
    for action in Action:
        count = action_counts.get(action, 0)
        if count:
            print(f"  {action.value}: {count}")

    if category_counts:
        print("  categories:")
        for category, count in sorted(category_counts.items()):
            print(f"    {category}: {count}")


def print_result_summary(results: list[TransferResult], manifest_path: Path) -> None:
    status_counts = Counter(result.status for result in results)
    print("Apply results")
    for status in Status:
        count = status_counts.get(status, 0)
        if count:
            print(f"  {status.value}: {count}")
    print(f"  manifest: {manifest_path}")


def print_progress(index: int, total: int, item, started: float) -> None:
    elapsed = monotonic() - started
    action = item.action.value
    print(f"[{index}/{total}] {action}: {item.source}", flush=True)
    if item.destination:
        print(f"  -> {item.destination}", flush=True)
    elif item.duplicate_of:
        print(f"  duplicate of {item.duplicate_of}", flush=True)
    if elapsed > 0 and index > 1:
        rate = index / elapsed
        print(f"  progress: {rate:.2f} files/sec", flush=True)


class LongFileProgressReporter:
    def __init__(self) -> None:
        self.started = monotonic()
        self.last_print = 0.0
        self.did_print = False

    def update(self, stage: str, current: int, total: int) -> None:
        now = monotonic()
        elapsed = now - self.started
        if elapsed < LONG_FILE_PROGRESS_DELAY_SECONDS:
            return
        if now - self.last_print < LONG_FILE_PROGRESS_INTERVAL_SECONDS and current < total:
            return

        self.last_print = now
        self.did_print = True
        percent = (current / total * 100) if total else 100.0
        bar = progress_bar(percent)
        print(
            f"\r  {stage} {bar} {percent:5.1f}% "
            f"({format_bytes(current)} / {format_bytes(total)})",
            end="",
            flush=True,
        )

    def finish(self) -> None:
        if self.did_print:
            print("", flush=True)


def progress_bar(percent: float, width: int = 20) -> str:
    filled = min(width, max(0, round(width * percent / 100)))
    return "[" + ("#" * filled) + ("." * (width - filled)) + "]"


def format_bytes(value: int) -> str | None:
    amount = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if amount < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(amount)} {unit}"
            return f"{amount:.1f} {unit}"
        amount /= 1024
