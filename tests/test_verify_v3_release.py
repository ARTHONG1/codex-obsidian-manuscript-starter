from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.test_blog_renderer import PYTHON


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins" / "obsidian-manuscript-publisher" / "skills" / "obsidian-manuscript-publisher" / "scripts" / "verify_v3_release.py"


class VerifyV3ReleaseTests(unittest.TestCase):
    def test_exporter_forces_utf8_console_output_on_windows(self):
        exporter = SCRIPT.parent / "export_publication_bundle.py"
        exporter = exporter.read_text(encoding="utf-8")
        self.assertIn('sys.stdout.reconfigure(encoding="utf-8")', exporter)
        self.assertIn('sys.stderr.reconfigure(encoding="utf-8")', exporter)

    def test_release_smoke_runs_native_validation_render_and_export(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run([str(PYTHON), str(SCRIPT), "--output", str(Path(temporary) / "verify")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "ready")
            self.assertIn(payload["desktop_export"], {"exported", "already_exported"})


if __name__ == "__main__":
    unittest.main()
