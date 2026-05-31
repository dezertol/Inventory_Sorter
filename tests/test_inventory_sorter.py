from __future__ import annotations

import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from inventory_sorter.cli import main
from inventory_sorter.hashutil import sha256_file
from inventory_sorter.transfer import safe_copy_verify_delete


class InventorySorterCliTests(unittest.TestCase):
    def test_preview_does_not_create_or_move_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            destination = root / "sorted"
            source.mkdir()
            sample = source / "photo.jpg"
            sample.write_bytes(b"image-bytes")

            exit_code = run_cli(
                "scan",
                str(source),
                "--destination",
                str(destination),
                "--preview",
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue(sample.exists())
            self.assertFalse(destination.exists())

    def test_apply_copies_verified_file_then_deletes_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            destination = root / "sorted"
            source.mkdir()
            sample = source / "invoice.pdf"
            sample.write_bytes(b"document-bytes")

            exit_code = run_cli(
                "scan",
                str(source),
                "--destination",
                str(destination),
                "--apply",
            )

            self.assertEqual(exit_code, 0)
            self.assertFalse(sample.exists())
            copied_files = list((destination / "Documents").glob("*/*.pdf"))
            self.assertEqual(len(copied_files), 1)
            self.assertEqual(copied_files[0].read_bytes(), b"document-bytes")

    def test_duplicate_source_is_only_deleted_with_remove_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            destination = root / "sorted"
            source.mkdir()
            existing_dir = destination / "Documents" / "2026-05"
            existing_dir.mkdir(parents=True)
            existing = existing_dir / "already.pdf"
            existing.write_bytes(b"same-bytes")
            duplicate = source / "duplicate.pdf"
            duplicate.write_bytes(b"same-bytes")

            without_flag = run_cli(
                "scan",
                str(source),
                "--destination",
                str(destination),
                "--apply",
            )
            self.assertEqual(without_flag, 0)
            self.assertTrue(duplicate.exists())

            with_flag = run_cli(
                "scan",
                str(source),
                "--destination",
                str(destination),
                "--apply",
                "--remove-duplicates",
            )
            self.assertEqual(with_flag, 0)
            self.assertFalse(duplicate.exists())
            self.assertTrue(existing.exists())

    def test_transfer_does_not_use_metadata_preserving_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.bin"
            destination = root / "destination.bin"
            source.write_bytes(b"bytes")

            with patch("shutil.copy2", side_effect=OSError(95, "Operation not supported")):
                safe_copy_verify_delete(
                    source,
                    destination,
                    sha256_file(source),
                )

            self.assertFalse(source.exists())
            self.assertEqual(destination.read_bytes(), b"bytes")


def run_cli(*args: str) -> int:
    with redirect_stdout(StringIO()):
        return main(list(args))


if __name__ == "__main__":
    unittest.main()
