# Inventory Sorter

Safely organize files from a source directory tree into a separate destination
library. Files are copied, hash-verified, and only then removed from the source.

## Usage

Preview the work without changing files:

```bash
python3 -m inventory_sorter scan /path/to/source \
  --destination /path/to/sorted-library \
  --preview
```

Apply the plan:

```bash
python3 -m inventory_sorter scan /path/to/source \
  --destination /path/to/sorted-library \
  --apply
```

Remove source files that are already duplicated in the destination:

```bash
python3 -m inventory_sorter scan /path/to/source \
  --destination /path/to/sorted-library \
  --apply \
  --remove-duplicates
```

Show per-file details:

```bash
python3 -m inventory_sorter scan /path/to/source \
  --destination /path/to/sorted-library \
  --preview \
  --verbose
```

## Behavior

- `--destination` is required and must be separate from the source tree.
- `--preview` and `--apply` are mutually exclusive.
- The source tree is scanned recursively.
- Files are sorted into `Category/YYYY-MM/filename`.
- Duplicate detection uses file size plus SHA-256.
- Copies are verified by SHA-256 before the source file is deleted.
- Existing destination files are never overwritten.
- Unknown file types are sorted into `Other/YYYY-MM`.

## Date Selection

The sorter uses the best available date in this order:

1. Photo EXIF date, when Pillow is installed and the file contains EXIF data.
2. Filesystem created date, when available.
3. Filesystem modified date as the platform fallback.

Install optional EXIF support:

```bash
python3 -m pip install ".[exif]"
```
