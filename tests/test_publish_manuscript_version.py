from __future__ import annotations

import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from tests.test_blog_renderer import BlogPackageMixin, PYTHON, RENDERER
from tests import test_manuscript_renderer as manuscript_renderer_support


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = (
    REPOSITORY_ROOT
    / "plugins"
    / "obsidian-manuscript-publisher"
    / "skills"
    / "obsidian-manuscript-publisher"
    / "scripts"
)
BOOK_RENDERER = manuscript_renderer_support.RENDERER
BOOK_VALIDATOR = manuscript_renderer_support.VALIDATOR
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# The transport module is where read_vault_file / delete_and_verify actually live. Tests must patch
# them here, not on the publisher, so a renamed or newly-introduced deletion call fails loudly.
import save_via_obsidian_rest as rest_transport

import publish_manuscript_version as publisher


class PublishManuscriptVersionTests(BlogPackageMixin, unittest.TestCase):
    def test_destination_collision_does_not_overwrite_successful_local_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            (version_dir / publisher.REPORT_NAME).write_text(
                json.dumps({"status": "published", "files": []}), encoding="utf-8"
            )
            (version_dir / "artifact.md").write_text("artifact", encoding="utf-8")
            with (
                mock.patch.object(publisher, "list_vault_directory", return_value={"exists": True}),
                mock.patch.object(publisher, "save_and_verify") as save,
            ):
                with self.assertRaisesRegex(ValueError, "already exists"):
                    publisher.publish_version(Path("unused-config.json"), version_dir, "Projects/Example/v0.1")
            self.assertEqual(json.loads((version_dir / publisher.REPORT_NAME).read_text(encoding="utf-8"))["status"], "published")
            save.assert_not_called()

    def test_book_publication_rejects_html_or_pdf_bytes_not_in_validation_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            self.create_rendered_book(version_dir)
            report_path = version_dir / "asset-validation.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report["validated_outputs"] = {
                "manuscript.html": "0" * 64,
                "manuscript.pdf": "1" * 64,
            }
            report_path.write_text(json.dumps(report), encoding="utf-8")
            with mock.patch.object(publisher, "list_vault_directory") as remote_list:
                with self.assertRaisesRegex(ValueError, "validated output"):
                    publisher.publish_version(Path("unused-config.json"), version_dir, "Projects/Example/01 Manuscript/Part 1/01/v0.1")
            remote_list.assert_not_called()

    def test_generic_destination_requires_approved_root_and_immutable_version(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            (version_dir / "artifact.md").write_text("artifact", encoding="utf-8")
            for destination in (".obsidian/v0.1", "Projects/Example/latest", "Random/v0.1"):
                with self.subTest(destination=destination):
                    with mock.patch.object(publisher, "list_vault_directory") as remote_list:
                        with self.assertRaises(ValueError):
                            publisher.publish_version(Path("unused-config.json"), version_dir, destination)
                    remote_list.assert_not_called()

    def test_destination_allowlist_requires_approved_root_at_path_start(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            (version_dir / "artifact.md").write_text("artifact", encoding="utf-8")
            with mock.patch.object(publisher, "list_vault_directory") as remote_list:
                with self.assertRaises(ValueError):
                    publisher.publish_version(
                        Path("unused-config.json"), version_dir, "evil/01 Manuscript/Part/01/v0.1"
                    )
            remote_list.assert_not_called()
    def test_publisher_namespace_exposes_no_remote_deletion_capability(self):
        """The publisher must never be able to delete remote data (SKILL.md non-destructive rule).

        Asserted structurally rather than through a mock, because a mock created with create=True
        would pass even when the attribute does not exist.
        """
        for forbidden in ("delete_and_verify", "read_vault_file"):
            self.assertFalse(
                hasattr(publisher, forbidden),
                f"publisher unexpectedly exposes {forbidden}; the no-cleanup guarantee is at risk",
            )
        source = Path(publisher.__file__).read_text(encoding="utf-8")
        self.assertNotIn("delete_and_verify", source)

    def test_transport_deletion_helpers_exist_so_patch_targets_are_real(self):
        """Guards the tests themselves: the patch targets must exist at their definition site."""
        for required in ("delete_and_verify", "read_vault_file"):
            self.assertTrue(hasattr(rest_transport, required))

    def create_rendered_blog(self, version_dir: Path) -> None:
        blog, manifest, report = self.write_valid_package(version_dir)
        validation_result, validation = self.validate_package(blog, manifest, report)
        self.assertEqual(validation_result.returncode, 0, validation)
        render_result = subprocess.run(
            [str(PYTHON), str(RENDERER), str(blog), str(version_dir)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(render_result.returncode, 0, render_result.stderr)

    def create_rendered_book(self, version_dir: Path) -> set[str]:
        manuscript, manifest, report = manuscript_renderer_support.ManuscriptRendererTests().write_valid_package(version_dir)
        payload = json.loads(manuscript.read_text(encoding="utf-8"))
        original_source_markdown = str(payload.get("source_markdown") or "")
        payload["output_profile"] = "book_a4"
        payload["source_markdown"] = "Codex로 자동화 Skill 만들기.md"
        manuscript.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        if original_source_markdown and original_source_markdown != payload["source_markdown"]:
            original_source = version_dir / original_source_markdown
            if original_source.is_file():
                original_source.unlink()
        (version_dir / payload["source_markdown"]).write_text(
            "# Codex로 자동화 Skill 만들기\n\n검증된 출판 원고입니다.\n",
            encoding="utf-8",
        )
        (version_dir / "production-plan.json").write_text(
            json.dumps({"status": "verified", "steps": ["Skill 구현"]}, ensure_ascii=False),
            encoding="utf-8",
        )
        validation_result = subprocess.run(
            [str(PYTHON), str(BOOK_VALIDATOR), str(manuscript), str(manifest), str(report)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(validation_result.returncode, 0, validation_result.stderr)
        render_result = subprocess.run(
            [str(PYTHON), str(BOOK_RENDERER), str(manuscript), str(version_dir)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(render_result.returncode, 0, render_result.stderr)
        return {
            path.relative_to(version_dir).as_posix()
            for path in version_dir.rglob("*")
            if path.is_file() and path.name != publisher.REPORT_NAME
        }

    def test_report_upload_failure_quarantines_without_deleting_possibly_written_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            (version_dir / "artifact.md").write_text("verified artifact", encoding="utf-8")

            def fail_only_final_report(_config, vault_path, _content, _base_url):
                if vault_path.endswith(publisher.REPORT_NAME):
                    raise RuntimeError("simulated report upload failure")
                return vault_path

            with (
                mock.patch.object(publisher, "list_vault_directory", return_value=None),
                mock.patch.object(publisher, "save_and_verify", side_effect=fail_only_final_report),
                # Patch at the real definition site. Patching these names onto the publisher with
                # create=True fabricates attributes it does not have, which makes
                # assert_not_called() tautological and proves nothing about the no-cleanup rule.
                mock.patch.object(rest_transport, "read_vault_file") as read_remote,
                mock.patch.object(rest_transport, "delete_and_verify") as delete,
            ):
                with self.assertRaisesRegex(RuntimeError, "report upload failure"):
                    publisher.publish_version(
                        Path("unused-config.json"),
                        version_dir,
                        "Projects/Example/v0.1",
                    )

            report = json.loads((version_dir / publisher.REPORT_NAME).read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "publication_failed")
            self.assertEqual(report["phase"], "publication_report")
            self.assertEqual(report["remote_state"], "partial_publication_possible")
            self.assertEqual(
                report["quarantine"]["possibly_written_paths"],
                [
                    "Projects/Example/v0.1/artifact.md",
                    "Projects/Example/v0.1/publication-validation.json",
                ],
            )
            self.assertEqual(report["quarantine"]["status"], "required")
            self.assertEqual(report["quarantine"]["automatic_cleanup"], "disabled")
            read_remote.assert_not_called()
            delete.assert_not_called()

    def test_nested_publication_report_is_unexpected_before_any_rest_call(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            assets = version_dir / "assets"
            assets.mkdir()
            (version_dir / "artifact.md").write_text("artifact", encoding="utf-8")
            (assets / publisher.REPORT_NAME).write_text("{}", encoding="utf-8")

            with (
                mock.patch.object(publisher, "list_vault_directory") as remote_list,
                mock.patch.object(publisher, "save_and_verify") as save,
            ):
                with self.assertRaisesRegex(ValueError, "nested publication-validation.json"):
                    publisher.publish_version(
                        Path("unused-config.json"),
                        version_dir,
                        "Projects/Example/v0.1",
                    )

            remote_list.assert_not_called()
            save.assert_not_called()

    def test_root_symlink_is_rejected_without_writing_through_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            fake_symlink = SimpleNamespace(st_mode=stat.S_IFLNK, st_file_attributes=0)

            with (
                mock.patch.object(publisher.os, "lstat", return_value=fake_symlink),
                mock.patch.object(publisher, "_write_report") as write_report,
                mock.patch.object(publisher, "list_vault_directory") as remote_list,
            ):
                with self.assertRaisesRegex(ValueError, "symbolic link|reparse point"):
                    publisher.publish_version(
                        Path("unused-config.json"),
                        version_dir,
                        "Projects/Example/v0.1",
                    )

            write_report.assert_not_called()
            remote_list.assert_not_called()

    def test_root_windows_reparse_point_is_rejected_without_writing_through_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
            fake_junction = SimpleNamespace(
                st_mode=stat.S_IFDIR,
                st_file_attributes=reparse_flag,
            )

            with (
                mock.patch.object(publisher.os, "lstat", return_value=fake_junction),
                mock.patch.object(publisher, "_write_report") as write_report,
                mock.patch.object(publisher, "list_vault_directory") as remote_list,
            ):
                with self.assertRaisesRegex(ValueError, "reparse point"):
                    publisher.publish_version(
                        Path("unused-config.json"),
                        version_dir,
                        "Projects/Example/v0.1",
                    )

            write_report.assert_not_called()
            remote_list.assert_not_called()

    def test_junctioned_ancestor_is_rejected_before_report_or_rest_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            version_dir = root / "junctioned" / "v0.1"
            version_dir.mkdir(parents=True)
            original_reason = publisher._unsafe_link_reason

            def fake_reason(path: Path):
                if Path(path).name == "junctioned":
                    return "reparse point"
                return original_reason(path)

            with (
                mock.patch.object(publisher, "_unsafe_link_reason", side_effect=fake_reason),
                mock.patch.object(publisher, "_write_report") as write_report,
                mock.patch.object(publisher, "list_vault_directory") as remote_list,
                mock.patch.object(publisher, "save_and_verify") as save,
            ):
                with self.assertRaisesRegex(ValueError, "reparse point"):
                    publisher.publish_version(
                        Path("unused-config.json"),
                        version_dir,
                        "Projects/Example/v0.1",
                    )

            write_report.assert_not_called()
            remote_list.assert_not_called()
            save.assert_not_called()

    def test_adaptive_blog_publication_rejects_tampered_rendered_markdown(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            self.create_rendered_blog(version_dir)
            with (version_dir / "blog.md").open("a", encoding="utf-8") as stream:
                stream.write("\n변조된 공개 문장\n")

            with mock.patch.object(publisher, "save_and_verify") as save:
                with self.assertRaisesRegex(ValueError, "rendered blog output"):
                    publisher.publish_version(
                        Path("unused-config.json"),
                        version_dir,
                        "Projects/Example/02 Blog/school-plan-validation/v0.1",
                    )
            save.assert_not_called()

    def test_adaptive_blog_publication_rejects_unlisted_extra_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            self.create_rendered_blog(version_dir)
            (version_dir / "unlisted-secret.txt").write_text("must not be published", encoding="utf-8")

            with mock.patch.object(publisher, "save_and_verify") as save:
                with self.assertRaisesRegex(ValueError, "unexpected files"):
                    publisher.publish_version(
                        Path("unused-config.json"),
                        version_dir,
                        "Projects/Example/02 Blog/school-plan-validation/v0.1",
                    )
            save.assert_not_called()

    def test_blog_destination_requires_a_complete_adaptive_blog_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            (version_dir / "notes.md").write_text("not a blog package", encoding="utf-8")

            with mock.patch.object(publisher, "save_and_verify") as save:
                with self.assertRaisesRegex(ValueError, "blog.json"):
                    publisher.publish_version(
                        Path("unused-config.json"),
                        version_dir,
                        "Projects/Example/02 Blog/topic/v0.1",
                    )
            save.assert_not_called()

    def test_adaptive_blog_destination_slug_must_match_blog_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            self.create_rendered_blog(version_dir)

            with mock.patch.object(publisher, "save_and_verify") as save:
                with self.assertRaisesRegex(ValueError, "slug"):
                    publisher.publish_version(
                        Path("unused-config.json"),
                        version_dir,
                        "Projects/Example/02 Blog/different-topic/v0.1",
                    )
            save.assert_not_called()

    def test_book_a4_publication_rejects_unlisted_extra_file_before_rest(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            self.create_rendered_book(version_dir)
            (version_dir / "private-notes.txt").write_text("must stay local", encoding="utf-8")

            with (
                mock.patch.object(publisher, "list_vault_directory") as remote_list,
                mock.patch.object(publisher, "save_and_verify") as save,
            ):
                with self.assertRaisesRegex(ValueError, "unexpected files"):
                    publisher.publish_version(
                        Path("unused-config.json"),
                        version_dir,
                        "Projects/Example/01 Manuscript/Part 1/01/v0.1",
                    )

            remote_list.assert_not_called()
            save.assert_not_called()

    def test_book_a4_publication_rejects_stale_validation_before_rest(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            self.create_rendered_book(version_dir)
            manuscript = version_dir / "manuscript.json"
            payload = json.loads(manuscript.read_text(encoding="utf-8"))
            payload["title"] = "검증 뒤 바뀐 제목"
            manuscript.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

            with (
                mock.patch.object(publisher, "list_vault_directory") as remote_list,
                mock.patch.object(publisher, "save_and_verify") as save,
            ):
                with self.assertRaisesRegex(ValueError, "stale"):
                    publisher.publish_version(
                        Path("unused-config.json"),
                        version_dir,
                        "Projects/Example/01 Manuscript/Part 1/01/v0.1",
                    )

            remote_list.assert_not_called()
            save.assert_not_called()

    def test_book_a4_publication_uploads_only_the_exact_package_allowlist(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            expected_files = self.create_rendered_book(version_dir)
            uploaded: list[str] = []

            with (
                mock.patch.object(publisher, "list_vault_directory", return_value=None),
                mock.patch.object(
                    publisher,
                    "save_and_verify",
                    side_effect=lambda _config, path, _content, _base_url: uploaded.append(path) or path,
                ),
            ):
                report = publisher.publish_version(
                    Path("unused-config.json"),
                    version_dir,
                    "Projects/Example/01 Manuscript/Part 1/01/v0.1",
                )

            prefix = "Projects/Example/01 Manuscript/Part 1/01/v0.1/"
            self.assertEqual(
                {path.removeprefix(prefix) for path in uploaded if not path.endswith(publisher.REPORT_NAME)},
                expected_files,
            )
            self.assertEqual(report["status"], "published")

    def test_put_failure_before_write_quarantines_without_attempting_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            (version_dir / "01-first.md").write_text("first", encoding="utf-8")
            (version_dir / "02-second.md").write_text("second", encoding="utf-8")

            def fail_second(_config, vault_path, _content, _base_url):
                if vault_path.endswith("02-second.md"):
                    raise RuntimeError("simulated second upload failure")
                return vault_path

            with (
                mock.patch.object(publisher, "list_vault_directory", return_value=None),
                mock.patch.object(publisher, "save_and_verify", side_effect=fail_second),
                mock.patch.object(rest_transport, "read_vault_file") as read_remote,
                mock.patch.object(rest_transport, "delete_and_verify") as delete,
            ):
                with self.assertRaisesRegex(RuntimeError, "second upload failure"):
                    publisher.publish_version(
                        Path("unused-config.json"),
                        version_dir,
                        "Projects/Example/v0.1",
                    )

            report = json.loads((version_dir / publisher.REPORT_NAME).read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "publication_failed")
            self.assertEqual(report["remote_state"], "partial_publication_possible")
            self.assertEqual(
                report["quarantine"]["possibly_written_paths"],
                [
                    "Projects/Example/v0.1/01-first.md",
                    "Projects/Example/v0.1/02-second.md",
                ],
            )
            self.assertNotIn("rollback_status", report)
            read_remote.assert_not_called()
            delete.assert_not_called()

    def test_put_failure_after_write_never_deletes_a_concurrent_writers_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            version_dir = Path(temporary)
            first = version_dir / "01-first.md"
            second = version_dir / "02-second.md"
            first.write_text("first", encoding="utf-8")
            second.write_text("second", encoding="utf-8")
            remote: dict[str, bytes] = {}

            def fail_after_second_write(_config, vault_path, content, _base_url):
                remote[vault_path] = content
                if vault_path.endswith("02-second.md"):
                    remote["Projects/Example/v0.1/01-first.md"] = b"concurrent-writer"
                    raise RuntimeError("simulated failure after a concurrent update")
                return vault_path

            def read_remote(_config, vault_path, _base_url):
                return remote.get(vault_path)

            with (
                mock.patch.object(publisher, "list_vault_directory", return_value=None),
                mock.patch.object(publisher, "save_and_verify", side_effect=fail_after_second_write),
                mock.patch.object(rest_transport, "read_vault_file", side_effect=read_remote),
                mock.patch.object(rest_transport, "delete_and_verify") as delete,
            ):
                with self.assertRaisesRegex(RuntimeError, "concurrent update"):
                    publisher.publish_version(
                        Path("unused-config.json"),
                        version_dir,
                        "Projects/Example/v0.1",
                    )

            delete.assert_not_called()
            self.assertEqual(remote["Projects/Example/v0.1/01-first.md"], b"concurrent-writer")
            self.assertEqual(remote["Projects/Example/v0.1/02-second.md"], b"second")
            failure = json.loads((version_dir / publisher.REPORT_NAME).read_text(encoding="utf-8"))
            self.assertEqual(failure["remote_state"], "partial_publication_possible")
            self.assertEqual(
                failure["quarantine"]["possibly_written_paths"],
                [
                    "Projects/Example/v0.1/01-first.md",
                    "Projects/Example/v0.1/02-second.md",
                ],
            )


if __name__ == "__main__":
    unittest.main()
