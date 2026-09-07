"""Retired built-in book packages must never reach the REST transport."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "obsidian-manuscript-publisher" / "skills" / "obsidian-manuscript-publisher" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import publish_manuscript_version as publisher


class RetiredBookPublicationTests(unittest.TestCase):
    def assert_rejected_before_rest(self, version_dir: Path, destination: str) -> None:
        with (
            mock.patch.object(publisher, "list_vault_directory", return_value=None) as remote_list,
            mock.patch.object(publisher, "save_and_verify") as save,
        ):
            with self.assertRaisesRegex(ValueError, "book_a4_removed"):
                publisher.publish_version(Path("unused-config.json"), version_dir, destination)
        remote_list.assert_not_called()
        save.assert_not_called()
        report = json.loads((version_dir / publisher.REPORT_NAME).read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "publication_failed")
        self.assertEqual(report["phase"], "local_validation")
        self.assertEqual(report["files"], [])

    def test_all_builtin_book_versions_are_rejected_even_at_retained_destinations(self):
        for version in (None, 1, 2, 3):
            for destination in (
                "01 Manuscript/Example/Part 1/01/v0.1",
                "Projects/Example/Exports/raw/v0.1",
                "03 Custom Manuscript/Example/v0.1",
                "Projects/Example/02 Blog/topic/v0.1",
            ):
                with self.subTest(version=version, destination=destination), tempfile.TemporaryDirectory() as temporary:
                    version_dir = Path(temporary)
                    payload = {"output_profile": "book_a4"}
                    if version is not None:
                        payload["template_version"] = version
                    (version_dir / "manuscript.json").write_text(json.dumps(payload), encoding="utf-8")
                    self.assert_rejected_before_rest(version_dir, destination)

    def test_book_destinations_are_rejected_without_manuscript_metadata(self):
        for destination in (
            "01 Manuscript/Example/Part 1/01/v0.1",
            "Projects/Example/01 Manuscript/Part 1/01/v0.1",
            "01 Projects/Example/01 Manuscript/Part 1/01/v0.1",
        ):
            with self.subTest(destination=destination), tempfile.TemporaryDirectory() as temporary:
                version_dir = Path(temporary)
                (version_dir / "manuscript.pdf").write_bytes(b"%PDF-book-output")
                self.assert_rejected_before_rest(version_dir, destination)

    def test_legacy_or_malformed_manuscript_metadata_cannot_use_generic_fallback(self):
        for content in ('{}', '{"template_version": 1}', 'not JSON'):
            with self.subTest(content=content), tempfile.TemporaryDirectory() as temporary:
                version_dir = Path(temporary)
                (version_dir / "manuscript.json").write_text(content, encoding="utf-8")
                self.assert_rejected_before_rest(version_dir, "Projects/Example/Exports/raw/v0.1")


if __name__ == "__main__":
    unittest.main()
