from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.test_blog_renderer import PYTHON
from tests.test_manuscript_v3 import BookV3PackageMixin


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "obsidian-manuscript-publisher" / "skills" / "obsidian-manuscript-publisher" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import publish_manuscript_version as publisher


class BookV3PublicationTests(BookV3PackageMixin, unittest.TestCase):
    def test_canonical_v3_package_passes_publication_preflight_without_v2_aliases(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            manuscript, manifest, report = self.write_v3_package(version_dir)
            validated = subprocess.run([str(PYTHON), str(SCRIPTS / "validate_manuscript.py"), str(manuscript), str(manifest), str(report)], capture_output=True, text=True)
            self.assertEqual(validated.returncode, 0, validated.stderr)
            rendered = subprocess.run([str(PYTHON), str(SCRIPTS / "render_manuscript.py"), str(manuscript), str(version_dir)], capture_output=True, text=True)
            self.assertEqual(rendered.returncode, 0, rendered.stderr)
            (version_dir / "production-plan.json").write_text(json.dumps({"status": "verified"}), encoding="utf-8")

            with (
                mock.patch.object(publisher, "list_vault_directory", return_value=None),
                mock.patch.object(publisher, "save_and_verify") as save,
            ):
                result = publisher.publish_version(
                    Path("unused-config.json"),
                    version_dir,
                    "01 Manuscript/AAA AI Agent Automation/Part 1/07/v0.1",
                )

            self.assertEqual(result["status"], "published")
            self.assertGreater(save.call_count, 7)


if __name__ == "__main__":
    unittest.main()
