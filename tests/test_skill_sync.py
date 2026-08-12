from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.test_blog_renderer import PYTHON


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins" / "obsidian-manuscript-publisher" / "skills" / "obsidian-manuscript-publisher" / "scripts" / "verify_skill_sync.py"


class SkillSyncTests(unittest.TestCase):
    def test_compare_ignores_generated_files_and_reports_content_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            destination = root / "destination"
            source.mkdir()
            destination.mkdir()
            (source / "SKILL.md").write_text("source", encoding="utf-8")
            (destination / "SKILL.md").write_text("installed", encoding="utf-8")
            (destination / "old.pyc").write_bytes(b"generated")
            result = subprocess.run([str(PYTHON), str(SCRIPT), "--source", str(source), "--destination", str(destination)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "different")
            self.assertEqual(payload["changed"], ["SKILL.md"])
            self.assertEqual(payload["extra"], [])

    def test_promote_verifies_and_preserves_the_previous_install(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            destination = root / "destination"
            source.mkdir()
            destination.mkdir()
            (source / "SKILL.md").write_text("new", encoding="utf-8")
            (destination / "SKILL.md").write_text("old", encoding="utf-8")
            result = subprocess.run([str(PYTHON), str(SCRIPT), "--source", str(source), "--destination", str(destination), "--promote"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "promoted")
            self.assertEqual((destination / "SKILL.md").read_text(encoding="utf-8"), "new")
            self.assertTrue(Path(payload["backup"]).is_dir())
            self.assertEqual((Path(payload["backup"]) / "SKILL.md").read_text(encoding="utf-8"), "old")


if __name__ == "__main__":
    unittest.main()
