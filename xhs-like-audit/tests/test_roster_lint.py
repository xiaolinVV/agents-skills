import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def load_module(module_name: str, script_name: str):
    script_path = Path(__file__).resolve().parents[1] / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LINT_MODULE = load_module("lint_roster", "lint_roster.py")
PARSE_MODULE = load_module("parse_roster", "parse_roster.py")
START_BATCH = Path(__file__).resolve().parents[1] / "scripts" / "start_batch.py"


class RosterLintTests(unittest.TestCase):
    def test_lint_roster_flags_cross_group_similarity_and_malformed_alias(self):
        roster_text = """口袋的小红📖
"评口袋的小红📖
口口👩"
是周一啊
"周一（孕期）
美静、"
蓝眼泪（爆🎉
"""

        roster = PARSE_MODULE.parse_roster_text(roster_text)
        report = LINT_MODULE.lint_roster(roster)

        self.assertEqual(len(roster), 5)
        self.assertGreaterEqual(report["summary"]["warning_count"], 3)

        warning_codes = {warning["code"] for warning in report["warnings"]}
        self.assertIn("similar-name-cross-group", warning_codes)
        self.assertIn("ambiguous-core-cross-group", warning_codes)
        self.assertIn("unbalanced-brackets", warning_codes)

        messages = "\n".join(warning["message"] for warning in report["warnings"])
        self.assertIn("口袋的小红📖", messages)
        self.assertIn("是周一啊", messages)
        self.assertIn("蓝眼泪（爆🎉", messages)

    def test_start_batch_writes_roster_lint_report_without_blocking_creation(self):
        roster_text = """口袋的小红📖
"评口袋的小红📖
口口👩"
蓝眼泪（爆🎉
"""

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            roster_file = tmp_path / "roster.txt"
            roster_file.write_text(roster_text, encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(START_BATCH),
                    "--roster-file",
                    str(roster_file),
                    "--batch-root",
                    str(tmp_path),
                    "--batch-name",
                    "lint-batch",
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            batch_dir = tmp_path / "lint-batch"
            lint_file = batch_dir / "roster-lint.txt"

            self.assertTrue(batch_dir.is_dir())
            self.assertTrue(lint_file.is_file())
            self.assertIn("Roster lint:", result.stderr)

            lint_text = lint_file.read_text(encoding="utf-8")
            self.assertIn("similar-name-cross-group", lint_text)
            self.assertIn("unbalanced-brackets", lint_text)

            next_steps = (batch_dir / "next-steps.txt").read_text(encoding="utf-8")
            self.assertIn("roster-lint.txt", next_steps)
            self.assertIn("roster has warning(s)", next_steps)


if __name__ == "__main__":
    unittest.main()
