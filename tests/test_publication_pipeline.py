from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tests.test_blog_renderer import BlogPackageMixin, PYTHON, RENDERER


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = (
    REPOSITORY_ROOT
    / "plugins"
    / "obsidian-manuscript-publisher"
    / "skills"
    / "obsidian-manuscript-publisher"
    / "scripts"
)
PUBLISHER_PATH = SCRIPTS_ROOT / "publish_manuscript_version.py"
VERSIONER_PATH = SCRIPTS_ROOT / "next_version.py"


def load_script(name: str, path: Path):
    scripts_root = str(SCRIPTS_ROOT)
    if scripts_root not in sys.path:
        sys.path.insert(0, scripts_root)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PublicationPipelineTests(BlogPackageMixin, unittest.TestCase):
    def setUp(self):
        self.publisher = load_script("obsidian_version_publisher_test", PUBLISHER_PATH)

    def write_blog_version(self, root: Path) -> tuple[Path, dict[str, bytes]]:
        version = root / "v0.1"
        version.mkdir(parents=True)
        blog, manifest, report = self.write_valid_package(version)
        validation_result, validation = self.validate_package(blog, manifest, report)
        self.assertEqual(validation_result.returncode, 0, validation)
        render_result = subprocess.run(
            [str(PYTHON), str(RENDERER), str(blog), str(version)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(render_result.returncode, 0, render_result.stderr)
        payloads = {
            path.relative_to(version).as_posix(): path.read_bytes()
            for path in version.rglob("*")
            if path.is_file()
        }
        return version, payloads

    def test_generic_publisher_sends_every_blog_artifact_as_original_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            version, payloads = self.write_blog_version(root)
            config = root / "data.json"
            config.write_text("{}", encoding="utf-8")
            uploads: list[tuple[str, bytes]] = []

            def capture_upload(_config, vault_path, content, _base_url=None):
                uploads.append((vault_path, content))
                return vault_path

            with (
                mock.patch.object(self.publisher, "list_vault_directory", return_value=None, create=True),
                mock.patch.object(self.publisher, "save_and_verify", side_effect=capture_upload),
            ):
                report = self.publisher.publish_version(
                    config,
                    version,
                    "01 Projects/AAA/02 Blog/school-plan-validation/v0.1",
                )

            uploaded = dict(uploads)
            for relative, content in payloads.items():
                remote = f"01 Projects/AAA/02 Blog/school-plan-validation/v0.1/{relative}"
                self.assertEqual(uploaded[remote], content)
            self.assertEqual(report["status"], "published")
            self.assertIn(
                "01 Projects/AAA/02 Blog/school-plan-validation/v0.1/publication-validation.json",
                uploaded,
            )

    def test_all_file_bytes_are_snapshotted_before_the_first_rest_call(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            version = root / "v0.1"
            version.mkdir()
            first = version / "01-first.bin"
            second = version / "02-second.bin"
            first.write_bytes(b"first-original")
            second.write_bytes(b"second-original")
            config = root / "data.json"
            config.write_text("{}", encoding="utf-8")
            uploads: dict[str, bytes] = {}

            def mutate_after_snapshot(_config, _vault_root, _base_url=None):
                first.write_bytes(b"first-mutated-after-rest-started")
                second.write_bytes(b"second-mutated-after-rest-started")
                return None

            def capture_upload(_config, vault_path, content, _base_url=None):
                uploads[vault_path] = content
                return vault_path

            with (
                mock.patch.object(
                    self.publisher,
                    "list_vault_directory",
                    side_effect=mutate_after_snapshot,
                    create=True,
                ),
                mock.patch.object(self.publisher, "save_and_verify", side_effect=capture_upload),
            ):
                self.publisher.publish_version(
                    config,
                    version,
                    "01 Projects/AAA/Exports/raw/v0.1",
                )

            prefix = "01 Projects/AAA/Exports/raw/v0.1/"
            self.assertEqual(uploads[prefix + "01-first.bin"], b"first-original")
            self.assertEqual(uploads[prefix + "02-second.bin"], b"second-original")

    def test_refuses_to_overwrite_an_existing_remote_version(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            version, _ = self.write_blog_version(root)
            config = root / "data.json"
            config.write_text("{}", encoding="utf-8")

            with (
                mock.patch.object(
                    self.publisher,
                    "list_vault_directory",
                    return_value=["blog.md", "blog.html"],
                    create=True,
                ),
                mock.patch.object(self.publisher, "save_and_verify") as save,
            ):
                with self.assertRaisesRegex(ValueError, "immutable"):
                    self.publisher.publish_version(
                        config,
                        version,
                        "01 Projects/AAA/02 Blog/school-plan-validation/v0.1",
                    )
            save.assert_not_called()
            self.assertFalse((version / "publication-validation.json").exists())

    def test_report_upload_failure_records_non_destructive_quarantine(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            version, payloads = self.write_blog_version(root)
            config = root / "data.json"
            config.write_text("{}", encoding="utf-8")
            remote: dict[str, bytes] = {}

            def fail_final_report(_config, vault_path, content, _base_url=None):
                remote[vault_path] = content
                if vault_path.endswith("/publication-validation.json"):
                    raise ConnectionError("simulated report upload failure")
                return vault_path

            with (
                mock.patch.object(self.publisher, "list_vault_directory", return_value=None, create=True),
                mock.patch.object(self.publisher, "save_and_verify", side_effect=fail_final_report),
                mock.patch.object(
                    self.publisher,
                    "read_vault_file",
                    side_effect=lambda _config, path, _base_url=None: remote.get(path),
                    create=True,
                ),
                mock.patch.object(
                    self.publisher,
                    "delete_and_verify",
                    create=True,
                ) as delete,
            ):
                with self.assertRaisesRegex(ConnectionError, "report upload failure"):
                    self.publisher.publish_version(
                        config,
                        version,
                        "01 Projects/AAA/02 Blog/school-plan-validation/v0.1",
                    )

            failure = json.loads((version / "publication-validation.json").read_text(encoding="utf-8"))
            self.assertEqual(failure["status"], "publication_failed")
            self.assertIn("report upload failure", failure["error"])
            self.assertEqual(failure["remote_state"], "partial_publication_possible")
            self.assertEqual(failure["quarantine"]["status"], "required")
            self.assertEqual(failure["quarantine"]["automatic_cleanup"], "disabled")
            self.assertEqual(
                set(failure["quarantine"]["possibly_written_paths"]),
                set(remote),
            )
            delete.assert_not_called()

    def test_blog_version_allocator_preserves_existing_versions(self):
        versioner = load_script("obsidian_version_allocator_test", VERSIONER_PATH)
        with tempfile.TemporaryDirectory() as temporary:
            blog_root = Path(temporary) / "02 Blog" / "portable-topic"
            (blog_root / "v0.1").mkdir(parents=True)
            (blog_root / "v0.7").mkdir()

            self.assertEqual(versioner.next_version(blog_root), "v0.8")
            self.assertTrue((blog_root / "v0.1").is_dir())
            self.assertTrue((blog_root / "v0.7").is_dir())


if __name__ == "__main__":
    unittest.main()
