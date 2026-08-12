from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.test_manuscript_v3 import BookV3PackageMixin


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "obsidian-manuscript-publisher" / "skills" / "obsidian-manuscript-publisher" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import finalize_publication as finalizer


class FinalizePublicationTests(BookV3PackageMixin, unittest.TestCase):
    def _arguments(self, version_dir: Path, root: Path) -> finalizer.FinalizeRequest:
        runtime = root / "runtime.json"
        runtime.write_text(json.dumps({"restDataPath": str(root / "rest-data.json")}), encoding="utf-8")
        (root / "rest-data.json").write_text("{}", encoding="utf-8")
        return finalizer.FinalizeRequest(
            source_version_dir=version_dir,
            config_path=runtime,
            vault_relative_version_dir="01 Manuscript/AAA AI Agent Automation/Part 1/07/v0.1",
            publication_root=root / "Desktop" / "옵시디언 원고",
            project_destination_root="AAA AI Agent Automation",
            vault_path=root / "Codex-Wiki",
        )

    def test_finalizer_orders_fresh_validation_native_render_vault_attempt_and_desktop_export(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            version_dir = root / "v0.1"
            version_dir.mkdir()
            self.write_v3_package(version_dir)
            (version_dir / "production-plan.json").write_text(json.dumps({"status": "verified"}), encoding="utf-8")
            calls: list[str] = []

            original_validate = finalizer.validate_manuscript.main
            original_render = finalizer.render_manuscript.main

            def validate(argv):
                calls.append("validate")
                return original_validate(argv)

            def render(json_path, output_dir):
                calls.append("render")
                return original_render(json_path, output_dir)

            def publish(*_args, **_kwargs):
                calls.append("publish")
                return {"status": "published", "files": []}

            def export(_request):
                calls.append("export")
                return {"status": "exported", "latest_path": "safe-relative-result"}

            with (
                mock.patch.object(finalizer.validate_manuscript, "main", side_effect=validate),
                mock.patch.object(finalizer.render_manuscript, "main", side_effect=render),
                mock.patch.object(finalizer.publisher, "publish_version", side_effect=publish),
                mock.patch.object(finalizer.exporter, "export_publication_bundle", side_effect=export),
            ):
                result = finalizer.finalize_publication(self._arguments(version_dir, root))

            self.assertEqual(calls, ["validate", "render", "publish", "export"])
            self.assertEqual(result["status"], "finalized")
            self.assertEqual(result["vault_publication_status"], "published")
            self.assertEqual(result["desktop_export_status"], "exported")

    def test_finalizer_exports_when_vault_publication_attempt_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            version_dir = root / "v0.1"
            version_dir.mkdir()
            self.write_v3_package(version_dir)
            (version_dir / "production-plan.json").write_text(json.dumps({"status": "verified"}), encoding="utf-8")

            with (
                mock.patch.object(finalizer.publisher, "publish_version", side_effect=RuntimeError("loopback unavailable")),
                mock.patch.object(finalizer.exporter, "export_publication_bundle", return_value={"status": "exported", "latest_path": "safe-relative-result"}),
            ):
                result = finalizer.finalize_publication(self._arguments(version_dir, root))

            self.assertEqual(result["vault_publication_status"], "publication_failed")
            self.assertEqual(result["desktop_export_status"], "exported")
            self.assertEqual(result["status"], "finalized_with_publication_failure")


if __name__ == "__main__":
    unittest.main()
