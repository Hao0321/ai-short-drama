"""Both linters read and report UTF-8 regardless of the platform locale codec.

Agents capture lint output through a pipe. On Windows that pipe defaults to the
locale codec (cp950, cp1252), which cannot encode Simplified Chinese, and stdin
is decoded with the same codec without stripping a UTF-8 BOM.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOM = b"\xef\xbb\xbf"

# Fictional pack: Simplified Chinese throughout, one unknown debt the linter echoes back.
PACK = {
    "project": {"title": "重生之我是总裁", "market": "中国大陆", "format": "竖屏短剧",
                "episode_duration_seconds": 90, "planned_episodes": 1},
    "premise_contract": {"public_identity": "外卖员", "hidden_truth": "集团继承人", "engine": "身份反转",
                         "season_question": "他何时摊牌", "fresh_twist": "系统反噬"},
    "characters": [{"id": "lead", "name": "林凡", "public_identity": "外卖员", "hidden_truth": "继承人"}],
    "locations": [{"id": "office", "name": "总部大厅"}],
    "episodes": [{"id": "ep_001", "hook": "开场被羞辱", "turn": "工牌掉落", "payoff": "亮出工牌",
                  "cliffhanger": "董事长来电", "characters": ["lead"], "locations": ["office"],
                  "state_delta": ["身份曝光"], "debts_opened": [], "debts_paid": ["还债承诺"]}],
}


def run_lint(script: str, args: list[str], stdin: bytes | None = None) -> subprocess.CompletedProcess:
    # Drop the overrides that would hide the locale default, as on a stock Windows shell.
    environment = {key: value for key, value in os.environ.items()
                   if key not in {"PYTHONIOENCODING", "PYTHONUTF8"}}
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), *args],
        input=stdin, capture_output=True, env=environment, timeout=60,
    )


class LintCliEncodingTests(unittest.TestCase):
    def test_drama_lint_reports_simplified_chinese_from_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            pack = Path(temporary) / "pack.json"
            pack.write_text(json.dumps(PACK, ensure_ascii=False), encoding="utf-8")
            completed = run_lint("drama_lint.py", [str(pack)])
        self.assertEqual(completed.returncode, 1, completed.stderr.decode("utf-8", "replace"))
        output = completed.stdout.decode("utf-8")
        self.assertTrue(output.startswith("INVALID: 1 error(s)"), output)
        self.assertIn("pays unknown debt: 还债承诺", output)

    def test_drama_lint_reads_bom_stdin_and_emits_json(self):
        stdin = BOM + json.dumps(PACK, ensure_ascii=False).encode("utf-8")
        completed = run_lint("drama_lint.py", ["-", "--json"], stdin)
        self.assertEqual(completed.returncode, 1, completed.stderr.decode("utf-8", "replace"))
        report = json.loads(completed.stdout.decode("utf-8"))
        self.assertEqual(report["error_count"], 1)
        self.assertIn("还债承诺", report["findings"][0]["message"])

    def test_studio_lint_reads_bom_stdin_of_the_example(self):
        example = (ROOT / "examples" / "studio-plan.example.json").read_bytes()
        completed = run_lint("studio_lint.py", ["-", "--studio-ready"], BOM + example.lstrip(BOM))
        self.assertEqual(completed.returncode, 0, completed.stdout.decode("utf-8", "replace"))
        self.assertTrue(completed.stdout.decode("utf-8").startswith("VALID"))

    def test_studio_lint_reports_simplified_chinese_from_stdin(self):
        plan = json.loads((ROOT / "examples" / "studio-plan.example.json").read_text(encoding="utf-8-sig"))
        plan["format_profile"]["id"] = "总裁逆袭"
        completed = run_lint("studio_lint.py", ["-"], json.dumps(plan, ensure_ascii=False).encode("utf-8"))
        self.assertEqual(completed.returncode, 1, completed.stderr.decode("utf-8", "replace"))
        self.assertIn("unknown format profile: '总裁逆袭'", completed.stdout.decode("utf-8"))

    def test_undecodable_stdin_is_a_lint_error_not_a_crash(self):
        completed = run_lint("drama_lint.py", ["-"], b"\xff\xfe{")
        self.assertEqual(completed.returncode, 1)
        self.assertIn("cannot read valid JSON", completed.stdout.decode("utf-8"))
        self.assertEqual(completed.stderr, b"")


if __name__ == "__main__":
    unittest.main()
