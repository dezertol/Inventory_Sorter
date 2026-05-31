from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path


EXIF_DATE_FORMATS = (
    "%Y:%m:%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
)


def best_sort_date(path: Path) -> datetime:
    exif_date = photo_exif_date(path)
    if exif_date is not None:
        return exif_date

    stat = path.stat()
    created_timestamp = filesystem_created_timestamp(stat)
    if created_timestamp:
        return datetime.fromtimestamp(created_timestamp)

    return datetime.fromtimestamp(stat.st_mtime)


def filesystem_created_timestamp(stat_result: os.stat_result) -> float | None:
    birthtime = getattr(stat_result, "st_birthtime", None)
    if birthtime is not None:
        return float(birthtime)
    if os.name == "nt":
        return float(stat_result.st_ctime)
    return None


def photo_exif_date(path: Path) -> datetime | None:
    if path.suffix.lower() not in {".jpg", ".jpeg", ".tiff", ".tif", ".heic", ".heif"}:
        return None

    try:
        from PIL import Image, ExifTags
    except ImportError:
        return None

    try:
        with Image.open(path) as image:
            exif = image.getexif()
    except Exception:
        return None

    if not exif:
        return None

    tag_names = {
        value: key
        for key, value in ExifTags.TAGS.items()
        if value in {"DateTimeOriginal", "DateTimeDigitized", "DateTime"}
    }

    for tag_name in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
        value = exif.get(tag_names.get(tag_name))
        if not value:
            continue
        parsed = parse_exif_datetime(str(value))
        if parsed is not None:
            return parsed

    return None


def parse_exif_datetime(value: str) -> datetime | None:
    cleaned = value.strip()
    for date_format in EXIF_DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, date_format)
        except ValueError:
            continue
    return None
