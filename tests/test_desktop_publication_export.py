from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import uuid
import multiprocessing

from tests.test_blog_renderer import BlogPackageMixin, PYTHON, RENDERER as BLOG_RENDERER
from tests import test_manuscript_renderer as manuscript_support


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = (
    REPOSITORY_ROOT
    / "plugins"
    / "obsidian-manuscript-publisher"
    / "skills"
    / "obsidian-manuscript-publisher"
    / "scripts"
)
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import export_publication_bundle as exporter


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


def create_directory_link(link: Path, target: Path) -> None:
    """Create a directory symlink or Windows junction for boundary tests."""

    try:
        os.symlink(target, link, target_is_directory=True)
        return
    except (OSError, NotImplementedError):
        pass
    if os.name == "nt":
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0:
            return
        raise unittest.SkipTest(f"directory link is unavailable: {result.stderr or result.stdout}")
    raise unittest.SkipTest("directory symlink is unavailable")


class PublicationExportTestCase(BlogPackageMixin, unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.sources = self.root / "sources"
        self.publication_root = self.root / "Desktop" / "옵시디언 원고"
        self.vault_root = self.root / "Codex-Wiki"
        self.sources.mkdir()
        self.vault_root.mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def create_rendered_book(self, version: str = "v0.1") -> Path:
        version_dir = self.sources / "book" / version
        version_dir.mkdir(parents=True)
        manuscript, manifest, report = manuscript_support.ManuscriptRendererTests().write_valid_package(version_dir)
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
            "# Codex로 자동화 Skill 만들기\n\n"
            "![미리보기](assets/preview.png)\n\n"
            "![Step 1](assets/step-01.png)\n\n"
            "![실전 활용](assets/real-world-use.png)\n",
            encoding="utf-8",
        )
        (version_dir / "production-plan.json").write_text(
            json.dumps({"status": "verified", "steps": ["Skill 구현"]}, ensure_ascii=False),
            encoding="utf-8",
        )
        validation = subprocess.run(
            [str(PYTHON), str(manuscript_support.VALIDATOR), str(manuscript), str(manifest), str(report)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(validation.returncode, 0, validation.stderr)
        rendered = subprocess.run(
            [str(PYTHON), str(manuscript_support.RENDERER), str(manuscript), str(version_dir)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(rendered.returncode, 0, rendered.stderr)
        return version_dir

    def create_rendered_blog(self, version: str = "v0.1") -> Path:
        version_dir = self.sources / "blog" / version
        version_dir.mkdir(parents=True)
        blog, manifest, report = self.write_valid_package(version_dir)
        validation, result = self.validate_package(blog, manifest, report)
        self.assertEqual(validation.returncode, 0, result)
        rendered = subprocess.run(
            [str(PYTHON), str(BLOG_RENDERER), str(blog), str(version_dir)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(rendered.returncode, 0, rendered.stderr)
        return version_dir

    def request(self, version_dir: Path, *, project: str = "AAA AI Agent Automation"):
        return exporter.ExportRequest(
            source_version_dir=version_dir,
            publication_root=self.publication_root,
            project_destination_root=project,
            vault_path=self.vault_root,
        )


class ValidBundleTests(PublicationExportTestCase):
    def test_nested_registry_destination_root_is_preserved_as_a_safe_relative_path(self):
        source = self.create_rendered_book()
        result = exporter.export_publication_bundle(exporter.ExportRequest(
            source_version_dir=source,
            publication_root=self.publication_root,
            project_destination_root="01 Manuscript/AAA AI Agent Automation",
            vault_path=self.vault_root,
        ))

        self.assertEqual(result["status"], "exported")
        self.assertTrue(Path(result["latest_path"]).is_dir())
        self.assertIn("AAA AI Agent Automation", str(result["latest_path"]))

    def test_book_v2_string_body_is_preserved_in_copy_text(self):
        source = self.create_rendered_book()
        manuscript = source / "manuscript.json"
        payload = json.loads(manuscript.read_text(encoding="utf-8"))
        payload["template_version"] = 2
        preparation_visual = payload["real_world_use_visual"]
        preparation_visual["caption"] = "그림 1-01-2. 검증에 필요한 준비 자료 예시"
        step_visual = payload["steps"][0]["visual"]
        step_visual["caption"] = "그림 1-01-3. 검증 흐름을 구현한 예시 화면"
        payload["practice_preparation"] = {"body": "자료를 준비합니다.", "visual": preparation_visual}
        payload["practice_blocks"] = [{
            "type": "step", "number": 1, "title": "검증 흐름 구현",
            "body": "첫 문장을 온전히 보존합니다. 둘째 문장도 온전히 보존합니다.",
            "step_kind": "build", "build_action": "검증 흐름을 구현합니다.",
            "artifact": {"name": "검증 흐름", "paths": ["app.py"], "status": "verified"},
            "completion_check": "테스트 결과를 확인합니다.",
            "interaction": {"user_request": "구현을 요청합니다.", "codex_action": "기능을 구현합니다.", "user_check": "결과를 확인합니다."},
            "visual": step_visual,
        }]
        payload["real_world_use_visual"] = None
        payload["verification_note"] = "실제 적용 전에 확인합니다."
        payload.pop("steps", None)
        payload.pop("tip", None)
        manuscript.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        manifest = source / "asset-manifest.json"
        manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
        manifest_payload["assets"] = [record for record in manifest_payload["assets"] if record["asset_id"] in {payload["preview"]["visual"]["asset_id"], payload["practice_preparation"]["visual"]["asset_id"], payload["practice_blocks"][0]["visual"]["asset_id"]}]
        manifest.write_text(json.dumps(manifest_payload, ensure_ascii=False), encoding="utf-8")
        report = source / "asset-validation.json"
        validation = subprocess.run([str(PYTHON), str(manuscript_support.VALIDATOR), str(manuscript), str(manifest), str(report)], capture_output=True, text=True)
        self.assertEqual(validation.returncode, 0, validation.stderr)
        rendered = subprocess.run([str(PYTHON), str(manuscript_support.RENDERER), str(manuscript), str(source)], capture_output=True, text=True)
        self.assertEqual(rendered.returncode, 0, rendered.stderr)

        result = exporter.export_publication_bundle(self.request(source))
        copy_text = (Path(result["latest_path"]) / "01 본문-복사용.txt").read_text(encoding="utf-8")
        self.assertIn("첫 문장을 온전히 보존합니다. 둘째 문장도 온전히 보존합니다.", copy_text)
        self.assertNotIn("첫 문 장 을", copy_text)

    def test_book_exports_copy_text_markdown_html_pdf_guide_and_numbered_images(self):
        source = self.create_rendered_book()
        result = exporter.export_publication_bundle(self.request(source))
        latest = Path(result["latest_path"])

        self.assertEqual(result["status"], "exported")
        self.assertEqual(result["profile"], "book_a4")
        self.assertEqual(
            {path.relative_to(latest).as_posix() for path in latest.rglob("*") if path.is_file()},
            {
                "01 본문-복사용.txt",
                "02 원고.md",
                "03 미리보기.html",
                "04 인쇄용.pdf",
                "05 이미지-삽입순서.md",
                "images/01-미리보기.png",
                "images/02-Step-01.png",
                "images/03-실전-활용.png",
                "_meta/export-manifest.json",
            },
        )
        copy_text = (latest / "01 본문-복사용.txt").read_text(encoding="utf-8")
        self.assertIn("[이번 챕터에서는]", copy_text)
        self.assertIn("Step 1. 자동화 Skill 구조와 실행 스크립트 구현", copy_text)
        self.assertIn("[이미지 02 삽입: 자동화 Skill 구조와 실행 스크립트 구현]", copy_text)
        self.assertNotIn("![", copy_text)
        markdown = (latest / "02 원고.md").read_text(encoding="utf-8")
        self.assertIn("images/01-미리보기.png", markdown)
        self.assertIn("images/02-Step-01.png", markdown)
        page = (latest / "03 미리보기.html").read_text(encoding="utf-8")
        self.assertIn("images/03-실전-활용.png", page)
        self.assertNotIn("file:///", page)
        self.assertEqual((latest / "04 인쇄용.pdf").read_bytes(), (source / "manuscript.pdf").read_bytes())
        manifest = json.loads((latest / "_meta" / "export-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["source_version"], "v0.1")
        self.assertEqual(manifest["vault_publication_status"], "not_published")

    def test_existing_managed_vault_shortcut_is_allowed_during_export(self):
        source = self.create_rendered_book()
        self.publication_root.mkdir(parents=True)
        shortcut = self.publication_root / exporter.MANAGED_VAULT_SHORTCUT
        shortcut.write_bytes(b"managed shortcut placeholder")

        result = exporter.export_publication_bundle(self.request(source))

        self.assertEqual(result["status"], "exported")
        self.assertEqual(shortcut.read_bytes(), b"managed shortcut placeholder")

    def test_blog_exports_copy_text_portable_preview_and_no_pdf(self):
        source = self.create_rendered_blog()
        result = exporter.export_publication_bundle(self.request(source))
        latest = Path(result["latest_path"])

        self.assertEqual(result["status"], "exported")
        self.assertEqual(result["profile"], "adaptive_blog")
        self.assertEqual(
            {path.relative_to(latest).as_posix() for path in latest.rglob("*") if path.is_file()},
            {
                "01 본문-복사용.txt",
                "02 블로그.md",
                "03 미리보기.html",
                "04 이미지-삽입순서.md",
                "images/01-대표이미지.png",
                "images/02-검증근거-1.png",
                "_meta/export-manifest.json",
            },
        )
        self.assertFalse(any(path.suffix.lower() == ".pdf" for path in latest.rglob("*")))
        copy_text = (latest / "01 본문-복사용.txt").read_text(encoding="utf-8")
        self.assertIn("[이미지 01 삽입: 대표이미지]", copy_text)
        self.assertIn("[이미지 02 삽입: 계획서를 다시 쓰게 되는 지점]", copy_text)
        markdown = (latest / "02 블로그.md").read_text(encoding="utf-8")
        self.assertIn("images/01-대표이미지.png", markdown)
        self.assertIn("images/02-검증근거-1.png", markdown)
        page = (latest / "03 미리보기.html").read_text(encoding="utf-8")
        self.assertIn("images/01-대표이미지.png", page)
        self.assertNotIn("assets/hero.png", page)
        guide = (latest / "04 이미지-삽입순서.md").read_text(encoding="utf-8")
        self.assertLess(guide.index("01-대표이미지.png"), guide.index("02-검증근거-1.png"))

    def test_root_index_is_offline_and_links_both_profiles(self):
        self.create_rendered_book()
        exporter.export_publication_bundle(self.request(self.sources / "book" / "v0.1"))
        self.create_rendered_blog()
        exporter.export_publication_bundle(self.request(self.sources / "blog" / "v0.1"))

        page = (self.publication_root / "00 원고 목록.html").read_text(encoding="utf-8")
        self.assertIn("AAA AI Agent Automation", page)
        self.assertIn("출판 원고형", page)
        self.assertIn("범용 블로그형", page)
        self.assertIn("01%20%EB%B3%B8%EB%AC%B8-%EB%B3%B5%EC%82%AC%EC%9A%A9.txt", page)
        self.assertIn(exporter.MANAGED_INDEX_MARKER, page)
        self.assertIn("검증 ready", page)
        self.assertIn("내보낸 시각", page)
        self.assertIn("폴더 열기", page)
        self.assertNotIn("<script", page.lower())
        self.assertNotRegex(page, r"https?://")


class ValidationAndSecurityTests(PublicationExportTestCase):
    def test_missing_runtime_dependency_returns_json_error_without_traceback(self):
        with mock.patch.object(
            exporter,
            "_load_runtime_dependencies",
            side_effect=ModuleNotFoundError("No module named 'PIL'"),
            create=True,
        ):
            with mock.patch.object(exporter, "export_publication_bundle") as export:
                result = exporter.main([
                    "--source-version-dir", "missing-source",
                    "--publication-root", "missing-publication",
                    "--project-destination-root", "01 Projects/Example",
                ])
        self.assertEqual(result, 1)
        export.assert_not_called()

    def assert_error_code(self, expected: str, request) -> None:
        with self.assertRaises(exporter.ExportError) as caught:
            exporter.export_publication_bundle(request)
        self.assertEqual(caught.exception.code, expected)

    def test_stale_validation_fails_before_publication_root_is_created(self):
        source = self.create_rendered_book()
        metadata = source / "manuscript.json"
        payload = json.loads(metadata.read_text(encoding="utf-8"))
        payload["title"] = "검증 뒤 바뀐 제목"
        metadata.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        self.assert_error_code("stale_validation", self.request(source))
        self.assertFalse(any(self.publication_root.rglob(".staging-*")))

    def test_unlisted_adjacent_file_is_rejected_and_never_copied(self):
        source = self.create_rendered_blog()
        (source / "private-notes.txt").write_text("must stay private", encoding="utf-8")

        self.assert_error_code("unexpected_source_file", self.request(source))
        self.assertFalse(self.publication_root.exists())

    def test_asset_hash_mismatch_is_rejected_before_latest_changes(self):
        source = self.create_rendered_blog()
        (source / "assets" / "hero.png").write_bytes(b"not an image")

        self.assert_error_code("asset_hash_mismatch", self.request(source))
        self.assertFalse(self.publication_root.exists())

    def test_project_destination_traversal_is_rejected(self):
        source = self.create_rendered_blog()
        self.assert_error_code("unsafe_path", self.request(source, project="../outside"))
        self.assertFalse((self.root / "Desktop" / "outside").exists())

    def test_vault_source_and_filesystem_roots_are_not_valid_publication_roots(self):
        source = self.create_rendered_blog()
        for unsafe_root in (self.vault_root, source, Path(source.anchor)):
            with self.subTest(root=str(unsafe_root)):
                request = exporter.ExportRequest(source, unsafe_root, "AAA", self.vault_root)
                self.assert_error_code("unsafe_path", request)

    def test_publication_root_must_not_be_inside_or_contain_the_vault(self):
        source = self.create_rendered_blog()
        for unsafe_root, vault in (
            (self.vault_root / "exports", self.vault_root),
            (self.root / "contains-vault", self.root / "contains-vault" / "Codex-Wiki"),
        ):
            with self.subTest(root=str(unsafe_root), vault=str(vault)):
                vault.mkdir(parents=True, exist_ok=True)
                request = exporter.ExportRequest(source, unsafe_root, "AAA", vault)
                self.assert_error_code("unsafe_path", request)

    def test_nested_publication_validation_file_is_not_ignored_by_source_allowlist(self):
        source = self.create_rendered_blog()
        (source / "assets" / "publication-validation.json").write_text("{}", encoding="utf-8")

        self.assert_error_code("unexpected_source_file", self.request(source))
        self.assertFalse(self.publication_root.exists())

    def test_unmanaged_root_usage_file_fails_before_latest_is_changed(self):
        first_source = self.create_rendered_book("v0.1")
        first = exporter.export_publication_bundle(self.request(first_source))
        latest = Path(first["latest_path"])
        before = tree_hashes(latest)
        usage = self.publication_root / "00 사용 방법.txt"
        usage.write_text("사용자가 직접 작성한 안내", encoding="utf-8")
        second_source = self.create_rendered_book("v0.2")

        self.assert_error_code("unmanaged_root_file", self.request(second_source))
        self.assertEqual(tree_hashes(latest), before)
        self.assertEqual(usage.read_text(encoding="utf-8"), "사용자가 직접 작성한 안내")

    def test_unmanaged_root_index_fails_before_latest_is_changed(self):
        first_source = self.create_rendered_blog("v0.1")
        first = exporter.export_publication_bundle(self.request(first_source))
        latest = Path(first["latest_path"])
        before = tree_hashes(latest)
        index = self.publication_root / "00 원고 목록.html"
        index.write_text("<html><body>사용자가 만든 목록</body></html>", encoding="utf-8")
        second_source = self.create_rendered_blog("v0.2")

        self.assert_error_code("unmanaged_root_file", self.request(second_source))
        self.assertEqual(tree_hashes(latest), before)
        self.assertEqual(index.read_text(encoding="utf-8"), "<html><body>사용자가 만든 목록</body></html>")

    def test_stray_publication_root_file_is_named_and_rejected(self):
        source = self.create_rendered_blog()
        self.publication_root.mkdir(parents=True)
        stray = self.publication_root / "unexpected.txt"
        stray.write_text("user file", encoding="utf-8")

        with self.assertRaises(exporter.ExportError) as caught:
            exporter.export_publication_bundle(self.request(source))

        self.assertEqual(caught.exception.code, "unexpected_root_file")
        self.assertIn(stray.name, str(caught.exception))

    def test_os_benign_publication_root_files_are_allowed(self):
        source = self.create_rendered_blog()
        self.publication_root.mkdir(parents=True)
        (self.publication_root / "desktop.ini").write_text("system", encoding="utf-8")
        (self.publication_root / "Thumbs.db").write_bytes(b"system")

        result = exporter.export_publication_bundle(self.request(source))

        self.assertEqual(result["status"], "exported")

    def test_cli_converts_filesystem_errors_to_stable_json_without_traceback(self):
        with mock.patch.object(exporter, "export_publication_bundle", side_effect=PermissionError("secret path")):
            with mock.patch("sys.stdout", new_callable=io.StringIO) as stdout:
                exit_code = exporter.main([
                    "--source-version-dir", "source",
                    "--publication-root", "publication",
                    "--project-destination-root", "AAA",
                ])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(payload, {
            "status": "failed",
            "code": "filesystem_error",
            "error": "filesystem_error: publication export could not access a required file",
        })

    def test_powershell_utf8_bom_managed_usage_allows_the_first_export(self):
        self.publication_root.mkdir(parents=True)
        usage = self.publication_root / "00 사용 방법.txt"
        usage.write_bytes(
            b"\xef\xbb\xbf"
            + (
                exporter.MANAGED_GUIDE_HEADER
                + "\nPowerShell installer initialized this managed file.\n"
            ).encode("utf-8")
        )
        source = self.create_rendered_blog()

        result = exporter.export_publication_bundle(self.request(source))

        self.assertEqual(result["status"], "exported")
        self.assertTrue(Path(result["latest_path"]).is_dir())
        self.assertTrue(usage.read_text(encoding="utf-8").startswith(exporter.MANAGED_GUIDE_HEADER))

    def test_existing_item_reparse_point_is_rejected_when_supported(self):
        source = self.create_rendered_blog()
        package = exporter.inspect_verified_package(self.request(source))
        escaped = self.root / "escaped-item"
        escaped.mkdir()
        project_root = self.publication_root / package.item_parts[0]
        project_root.mkdir(parents=True)
        profile_link = project_root / package.item_parts[1]
        try:
            os.symlink(escaped, profile_link, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"directory symlink is unavailable: {error}")

        self.assert_error_code("unsafe_path", self.request(source))
        self.assertEqual(list(escaped.iterdir()), [])

    def test_publication_root_reparse_point_is_rejected_before_resolution(self):
        source = self.create_rendered_blog()
        escaped = self.root / "escaped-publication-root"
        escaped.mkdir()
        alias = self.root / "publication-root-alias"
        create_directory_link(alias, escaped)
        request = exporter.ExportRequest(source, alias, "AAA", self.vault_root)

        self.assert_error_code("unsafe_path", request)
        self.assertEqual(list(escaped.iterdir()), [])

    def test_history_reparse_point_is_rejected_without_writing_to_its_target(self):
        first_source = self.create_rendered_book("v0.1")
        first = exporter.export_publication_bundle(self.request(first_source))
        latest = Path(first["latest_path"])
        escaped = self.root / "escaped-history"
        escaped.mkdir()
        create_directory_link(latest.parent / "99 이전버전", escaped)
        second_source = self.create_rendered_book("v0.2")

        self.assert_error_code("unsafe_path", self.request(second_source))
        self.assertEqual(list(escaped.iterdir()), [])
        self.assertEqual(
            json.loads((latest / "_meta" / "export-manifest.json").read_text(encoding="utf-8"))["source_version"],
            "v0.1",
        )

    def test_tampered_rendered_blog_output_is_rejected_as_stale(self):
        source = self.create_rendered_blog()
        (source / "blog.html").write_text("<script>tracking()</script>", encoding="utf-8")

        self.assert_error_code("stale_rendered_output", self.request(source))
        self.assertFalse(self.publication_root.exists())

    def test_source_mutation_between_inspection_and_bundle_build_is_rejected(self):
        source = self.create_rendered_blog()
        real_build = exporter.build_bundle

        def mutate_then_build(package, staging):
            (source / "blog.md").write_text("changed after inspection", encoding="utf-8")
            return real_build(package, staging)

        with mock.patch.object(exporter, "build_bundle", side_effect=mutate_then_build):
            self.assert_error_code("source_changed", self.request(source))
        self.assertFalse(any(self.publication_root.glob("**/00 최신본")))

    def test_sanitized_components_have_stable_collision_suffixes_and_reserved_names(self):
        colon = exporter.sanitize_component("A:B")
        question = exporter.sanitize_component("A?B")

        self.assertNotEqual(colon, question)
        self.assertTrue(colon.startswith("A_B--"))
        self.assertTrue(question.startswith("A_B--"))
        self.assertFalse(exporter.sanitize_component("CON.txt").upper().startswith("CON."))

    def test_windows_reserved_blog_slug_is_rejected(self):
        source = self.create_rendered_blog()
        metadata = source / "blog.json"
        validation = source / "blog-validation.json"
        payload = json.loads(metadata.read_text(encoding="utf-8"))
        payload["slug"] = "con"
        metadata.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        report = json.loads(validation.read_text(encoding="utf-8"))
        report["validated_inputs"]["blog_sha256"] = hashlib.sha256(metadata.read_bytes()).hexdigest()
        validation.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        self.assert_error_code("unsafe_path", self.request(source))


class VersionTransactionTests(PublicationExportTestCase):
    def test_identical_reexport_is_idempotent(self):
        source = self.create_rendered_book("v0.1")
        first = exporter.export_publication_bundle(self.request(source))
        latest = Path(first["latest_path"])
        before = tree_hashes(latest)

        second = exporter.export_publication_bundle(self.request(source))

        self.assertEqual(second["status"], "already_exported")
        self.assertEqual(tree_hashes(latest), before)

    def test_newer_version_archives_previous_latest(self):
        first_source = self.create_rendered_book("v0.1")
        first = exporter.export_publication_bundle(self.request(first_source))
        first_hashes = tree_hashes(Path(first["latest_path"]))
        second_source = self.create_rendered_book("v0.2")

        second = exporter.export_publication_bundle(self.request(second_source))
        latest = Path(second["latest_path"])
        history = latest.parent / "99 이전버전" / "v0.1"

        self.assertEqual(second["status"], "exported")
        self.assertEqual(json.loads((latest / "_meta" / "export-manifest.json").read_text(encoding="utf-8"))["source_version"], "v0.2")
        self.assertEqual(tree_hashes(history), first_hashes)

    def test_older_selected_version_is_added_to_history_without_replacing_latest(self):
        newer = self.create_rendered_blog("v0.2")
        newest_result = exporter.export_publication_bundle(self.request(newer))
        latest = Path(newest_result["latest_path"])
        before = tree_hashes(latest)
        older = self.create_rendered_blog("v0.1")

        result = exporter.export_publication_bundle(self.request(older))

        self.assertEqual(result["status"], "history_exported")
        self.assertEqual(tree_hashes(latest), before)
        self.assertTrue((latest.parent / "99 이전버전" / "v0.1" / "_meta" / "export-manifest.json").is_file())

    def test_corrupt_same_version_export_is_an_immutable_conflict(self):
        source = self.create_rendered_book("v0.1")
        result = exporter.export_publication_bundle(self.request(source))
        latest = Path(result["latest_path"])
        (latest / "01 본문-복사용.txt").write_text("tampered", encoding="utf-8")

        with self.assertRaises(exporter.ExportError) as caught:
            exporter.export_publication_bundle(self.request(source))
        self.assertEqual(caught.exception.code, "immutable_export_conflict")

    def test_manifest_hash_rewrite_cannot_preserve_a_forged_fingerprint(self):
        source = self.create_rendered_book("v0.1")
        result = exporter.export_publication_bundle(self.request(source))
        latest = Path(result["latest_path"])
        payload = latest / "01 본문-복사용.txt"
        payload.write_text("attacker-controlled replacement", encoding="utf-8")
        manifest_path = latest / "_meta" / "export-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["exported_files"]["01 본문-복사용.txt"] = hashlib.sha256(payload.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        with self.assertRaises(exporter.ExportError) as caught:
            exporter.export_publication_bundle(self.request(source))

        self.assertEqual(caught.exception.code, "immutable_export_conflict")

    def test_owned_partial_staging_is_removed_and_export_can_resume(self):
        source = self.create_rendered_blog("v0.1")
        result = exporter.export_publication_bundle(self.request(source))
        latest = Path(result["latest_path"])
        partial = latest.parent / f".staging-{uuid.uuid4().hex}"
        partial.mkdir()
        (partial / exporter.STAGING_OWNER_MARKER).write_text(exporter.STAGING_OWNER_VALUE, encoding="utf-8")
        (partial / "partial.tmp").write_text("interrupted", encoding="utf-8")

        repeated = exporter.export_publication_bundle(self.request(source))

        self.assertEqual(repeated["status"], "already_exported")
        self.assertFalse(partial.exists())

    def test_unowned_partial_staging_is_not_deleted(self):
        source = self.create_rendered_blog("v0.1")
        result = exporter.export_publication_bundle(self.request(source))
        latest = Path(result["latest_path"])
        unknown = latest.parent / f".staging-{uuid.uuid4().hex}"
        unknown.mkdir()
        (unknown / "user-file.txt").write_text("keep me", encoding="utf-8")

        with self.assertRaises(exporter.ExportError) as caught:
            exporter.export_publication_bundle(self.request(source))

        self.assertEqual(caught.exception.code, "recovery_invalid")
        self.assertEqual((unknown / "user-file.txt").read_text(encoding="utf-8"), "keep me")

    def test_recovers_previous_latest_after_interruption_before_new_promotion(self):
        first_source = self.create_rendered_book("v0.1")
        first = exporter.export_publication_bundle(self.request(first_source))
        latest = Path(first["latest_path"])
        item_root = latest.parent
        previous = item_root / ".previous-interrupted"
        os.replace(latest, previous)
        second_source = self.create_rendered_book("v0.2")

        result = exporter.export_publication_bundle(self.request(second_source))

        self.assertEqual(result["status"], "exported")
        self.assertEqual(
            json.loads((latest / "_meta" / "export-manifest.json").read_text(encoding="utf-8"))["source_version"],
            "v0.2",
        )
        history = item_root / "99 이전버전" / "v0.1"
        self.assertTrue((history / "_meta" / "export-manifest.json").is_file())
        self.assertFalse(previous.exists())

    def test_archives_verified_previous_after_interruption_following_new_promotion(self):
        first_source = self.create_rendered_blog("v0.1")
        first = exporter.export_publication_bundle(self.request(first_source))
        latest = Path(first["latest_path"])
        item_root = latest.parent
        previous = item_root / ".previous-interrupted"
        os.replace(latest, previous)
        second_source = self.create_rendered_blog("v0.2")
        staging = item_root / ".staging-interrupted"
        second_package = exporter.inspect_verified_package(self.request(second_source))
        exporter.build_bundle(second_package, staging)
        os.replace(staging, latest)

        result = exporter.export_publication_bundle(self.request(second_source))

        self.assertEqual(result["status"], "already_exported")
        history = item_root / "99 이전버전" / "v0.1"
        self.assertTrue((history / "_meta" / "export-manifest.json").is_file())
        self.assertFalse(previous.exists())

    def test_ambiguous_multiple_previous_bundles_stop_without_mutation(self):
        source = self.create_rendered_book("v0.1")
        result = exporter.export_publication_bundle(self.request(source))
        latest = Path(result["latest_path"])
        item_root = latest.parent
        previous_one = item_root / ".previous-one"
        previous_two = item_root / ".previous-two"
        os.replace(latest, previous_one)
        shutil.copytree(previous_one, previous_two)
        before_one = tree_hashes(previous_one)
        before_two = tree_hashes(previous_two)

        with self.assertRaises(exporter.ExportError) as caught:
            exporter.export_publication_bundle(self.request(source))

        self.assertEqual(caught.exception.code, "recovery_ambiguous")
        self.assertFalse(latest.exists())
        self.assertEqual(tree_hashes(previous_one), before_one)
        self.assertEqual(tree_hashes(previous_two), before_two)

    def test_failed_index_update_restores_previous_latest_and_index(self):
        first_source = self.create_rendered_blog("v0.1")
        first = exporter.export_publication_bundle(self.request(first_source))
        latest = Path(first["latest_path"])
        before_latest = tree_hashes(latest)
        index = self.publication_root / "00 원고 목록.html"
        before_index = index.read_bytes()
        second_source = self.create_rendered_blog("v0.2")

        with mock.patch.object(exporter, "regenerate_root_index", side_effect=OSError("injected index failure")):
            with self.assertRaises(OSError):
                exporter.export_publication_bundle(self.request(second_source))

        self.assertEqual(tree_hashes(latest), before_latest)
        self.assertEqual(index.read_bytes(), before_index)
        self.assertFalse(any(path.name.startswith((".staging-", ".previous-")) for path in latest.parent.iterdir()))

    def test_same_content_reexport_refreshes_vault_publication_status(self):
        source = self.create_rendered_blog("v0.1")
        first = exporter.export_publication_bundle(self.request(source))
        latest = Path(first["latest_path"])
        (source / "publication-validation.json").write_text(
            json.dumps({"status": "published"}, ensure_ascii=False),
            encoding="utf-8",
        )

        second = exporter.export_publication_bundle(self.request(source))

        self.assertEqual(second["status"], "already_exported")
        manifest = json.loads((latest / "_meta" / "export-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["vault_publication_status"], "published")
        index = (self.publication_root / "00 원고 목록.html").read_text(encoding="utf-8")
        self.assertIn("Obsidian published", index)

    def test_export_uses_cross_process_lock_and_reports_busy_root(self):
        source = self.create_rendered_blog("v0.1")
        lock_path = self.publication_root / exporter.EXPORT_LOCK_NAME
        self.publication_root.mkdir(parents=True, exist_ok=True)
        holder = lock_path.open("a+b")
        exporter._acquire_export_lock(holder)
        try:
            with self.assertRaises(exporter.ExportError) as caught:
                exporter.export_publication_bundle(self.request(source))
            self.assertEqual(caught.exception.code, "export_locked")
        finally:
            exporter._release_export_lock(holder)
            holder.close()

    def test_failed_promotion_leaves_read_only_incomplete_marker(self):
        first_source = self.create_rendered_blog("v0.1")
        exporter.export_publication_bundle(self.request(first_source))
        second_source = self.create_rendered_blog("v0.2")
        with mock.patch.object(exporter, "regenerate_root_index", side_effect=OSError("injected")):
            with self.assertRaises(OSError):
                exporter.export_publication_bundle(self.request(second_source))
        marker = self.publication_root / exporter.INCOMPLETE_MARKER
        self.assertTrue(marker.is_file())
        report = json.loads(marker.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["operation"], "publication_export")
        self.assertEqual(report["code"], "export_failed")
        self.assertEqual(report["owner"], exporter.INCOMPLETE_MARKER_OWNER)
        self.assertIn("error", report)
        self.assertNotIn("DELETE", marker.read_text(encoding="utf-8"))

    def test_success_does_not_delete_an_unowned_incomplete_marker(self):
        source = self.create_rendered_blog("v0.1")
        self.publication_root.mkdir(parents=True)
        marker = self.publication_root / exporter.INCOMPLETE_MARKER
        marker.write_text(json.dumps({"status": "incomplete", "owner": "someone-else"}), encoding="utf-8")

        with self.assertRaises(exporter.ExportError) as caught:
            exporter.export_publication_bundle(self.request(source))

        self.assertEqual(caught.exception.code, "unmanaged_root_file")
        self.assertTrue(marker.exists())

    def test_known_legacy_export_marker_is_cleared_after_a_successful_export(self):
        source = self.create_rendered_book("v0.1")
        self.publication_root.mkdir(parents=True)
        marker = self.publication_root / exporter.INCOMPLETE_MARKER
        marker.write_text(
            json.dumps({
                "status": "incomplete",
                "operation": "publication_export",
                "error": "legacy exporter interrupted",
                "read_only_report": True,
            }),
            encoding="utf-8",
        )

        result = exporter.export_publication_bundle(self.request(source))

        self.assertEqual(result["status"], "exported")
        self.assertFalse(marker.exists())

    def test_empty_assets_are_rejected_before_staging(self):
        source = self.create_rendered_blog("v0.1")
        manifest = source / "asset-manifest.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["assets"] = []
        manifest.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(exporter.ExportError) as direct:
            exporter._manifest_assets(source, data)
        self.assertEqual(direct.exception.code, "manifest_invalid")
        self.assertIn("at least one asset", str(direct.exception))
        with self.assertRaises(exporter.ExportError) as caught:
            exporter.export_publication_bundle(self.request(source))
        self.assertEqual(caught.exception.code, "stale_validation")
        self.assertFalse(self.publication_root.exists())

    def test_binary_asset_readback_matches_manifest_hash_and_mime(self):
        source = self.create_rendered_blog("v0.1")
        result = exporter.export_publication_bundle(self.request(source))
        latest = Path(result["latest_path"])
        asset = next(path for path in latest.rglob("*.png"))
        manifest = json.loads((latest / "_meta" / "export-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["exported_files"][asset.relative_to(latest).as_posix()], hashlib.sha256(asset.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
