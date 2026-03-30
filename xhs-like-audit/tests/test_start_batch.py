import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "start_batch.py"


class StartBatchZipImportTests(unittest.TestCase):
    def test_start_batch_accepts_zip_and_builds_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            roster_file = tmp_path / "roster.txt"
            roster_file.write_text("红蓝霸霸\n", encoding="utf-8")

            zip_file = tmp_path / "screenshots.zip"
            with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("a.jpg", b"fake-image-a")
                zf.writestr("nested/b.png", b"fake-image-b")
                zf.writestr("notes.txt", "ignore me")
                zf.writestr("__MACOSX/._a.jpg", b"ignore me too")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--roster-file",
                    str(roster_file),
                    "--zip-file",
                    str(zip_file),
                    "--batch-root",
                    str(tmp_path),
                    "--batch-name",
                    "zip-batch",
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)

            batch_dir = tmp_path / "zip-batch"
            manifest = json.loads((batch_dir / "images-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["image_count"], 2)
            self.assertEqual(
                [item["relative_path"] for item in manifest["images"]],
                ["a.jpg", "nested/b.png"],
            )
            self.assertTrue((batch_dir / "images" / "a.jpg").is_file())
            self.assertTrue((batch_dir / "images" / "nested" / "b.png").is_file())
            self.assertFalse((batch_dir / "images" / "notes.txt").exists())

    def test_start_batch_rejects_unsafe_zip_paths_and_cleans_batch_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            roster_file = tmp_path / "roster.txt"
            roster_file.write_text("红蓝霸霸\n", encoding="utf-8")

            zip_file = tmp_path / "unsafe.zip"
            with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("../escape.jpg", b"bad")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--roster-file",
                    str(roster_file),
                    "--zip-file",
                    str(zip_file),
                    "--batch-root",
                    str(tmp_path),
                    "--batch-name",
                    "unsafe-batch",
                ],
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Unsafe zip member path", result.stderr)
            self.assertFalse((tmp_path / "unsafe-batch").exists())

    def test_large_zip_batch_mentions_parallel_sharding_in_next_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            roster_file = tmp_path / "roster.txt"
            roster_file.write_text("红蓝霸霸\n", encoding="utf-8")

            zip_file = tmp_path / "large.zip"
            with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as zf:
                for index in range(20):
                    zf.writestr(f"shot-{index:03d}.jpg", f"img-{index}".encode("utf-8"))

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--roster-file",
                    str(roster_file),
                    "--zip-file",
                    str(zip_file),
                    "--batch-root",
                    str(tmp_path),
                    "--batch-name",
                    "large-batch",
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            next_steps = (tmp_path / "large-batch" / "next-steps.txt").read_text(encoding="utf-8")
            self.assertIn("5-10 image shards", next_steps)
            self.assertIn("apply update_counts.py serially", next_steps)


if __name__ == "__main__":
    unittest.main()
