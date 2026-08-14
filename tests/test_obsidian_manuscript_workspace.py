from pathlib import Path
import json
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPOSITORY_ROOT / "plugins" / "obsidian-manuscript-publisher"
SKILL = PLUGIN_ROOT / "skills" / "obsidian-manuscript-publisher" / "SKILL.md"
PLUGIN_MANIFEST = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
README = REPOSITORY_ROOT / "README.md"
MARKETPLACE = REPOSITORY_ROOT / ".agents" / "plugins" / "marketplace.json"
INSTALL_PROMPT = REPOSITORY_ROOT / "INSTALL_PROMPT.md"
RELEASE = REPOSITORY_ROOT / "docs" / "RELEASE.md"
CITATION = REPOSITORY_ROOT / "CITATION.cff"
BLOG_SCHEMA = PLUGIN_ROOT / "skills" / "obsidian-manuscript-publisher" / "references" / "blog-schema.md"
BLOG_POLICY = PLUGIN_ROOT / "skills" / "obsidian-manuscript-publisher" / "references" / "blog-editorial-policy.md"
BOOK_SCHEMA = PLUGIN_ROOT / "skills" / "obsidian-manuscript-publisher" / "references" / "manuscript-schema.md"
ASSET_POLICY = PLUGIN_ROOT / "skills" / "obsidian-manuscript-publisher" / "references" / "asset-policy.md"
OPENAI_YAML = PLUGIN_ROOT / "skills" / "obsidian-manuscript-publisher" / "agents" / "openai.yaml"
PUBLICATION_LIBRARY = PLUGIN_ROOT / "skills" / "obsidian-manuscript-publisher" / "references" / "publication-library.md"


class ObsidianManuscriptWorkspaceTests(unittest.TestCase):
    def test_skill_supports_on_demand_refresh_and_versioned_synthesis(self):
        skill = SKILL.read_text(encoding="utf-8")
        for required_text in [
            "Archive and Refresh the Current Conversation",
            "This is an on-demand Codex action",
            "Synthesize a Manuscript Version",
            "manuscript.json",
            "render_manuscript.py",
            "v0.N",
            "A4",
        ]:
            self.assertIn(required_text, skill)

    def test_skill_has_codex_build_step_and_landscape_visual_policy(self):
        skill = SKILL.read_text(encoding="utf-8")
        for required_text in [
            "Flexible Build-Step Contract",
            '"user_request"',
            '"codex_action"',
            '"user_check"',
            "wide landscape composition, 16:9",
            "view_image",
            "numbered editorial caption",
            "ui_screen",
            "absence of generic AI motifs",
        ]:
            self.assertIn(required_text, skill)

    def test_skill_selects_independent_book_and_blog_output_profiles(self):
        skill = SKILL.read_text(encoding="utf-8")
        for required_text in [
            "Output Profile Selection",
            "book_a4",
            "adaptive_blog",
            "범용 블로그형",
            "블로그 버전",
            "둘 다",
            "book_a4 remains the default",
        ]:
            self.assertIn(required_text, skill)

    def test_skill_has_complete_adaptive_blog_pipeline(self):
        skill = SKILL.read_text(encoding="utf-8")
        for required_text in [
            "Synthesize an Adaptive Blog Version",
            "references/blog-schema.md",
            "references/blog-editorial-policy.md",
            "02 Blog/<topic-slug>/v0.N",
            "validate_blog.py",
            "render_blog.py",
            "blog.md",
            "blog.html",
            "publication-validation.json",
            "publish_manuscript_version.py",
            "Do not create a PDF for this profile",
        ]:
            self.assertIn(required_text, skill)

    def test_public_metadata_exposes_blog_profile_as_version_0_5_1(self):
        manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], "0.5.1")
        self.assertIn("blog", manifest["description"].lower())
        self.assertIn("blog", manifest["interface"]["longDescription"].lower())

        readme = README.read_text(encoding="utf-8")
        for required_text in [
            "출판 원고형 (`book_a4`)",
            "범용 블로그형 (`adaptive_blog`)",
            "blog.md",
            "blog.html",
            "AI 탐지기",
        ]:
            self.assertIn(required_text, readme)

    def test_beginner_install_reference_keeps_release_pin_outside_local_marketplace_source(self):
        manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
        version = manifest["version"]
        tag = f"v{version}"
        marketplace = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
        source = marketplace["plugins"][0]["source"]

        self.assertEqual(set(source), {"source", "path"})
        self.assertEqual(source["source"], "local")
        self.assertEqual(source["path"], "./plugins/obsidian-manuscript-publisher")
        for document in (README, INSTALL_PROMPT, RELEASE):
            self.assertIn(tag, document.read_text(encoding="utf-8"))
        self.assertIn(f"version: {version}", CITATION.read_text(encoding="utf-8"))
        self.assertTrue((REPOSITORY_ROOT / "docs" / f"RELEASE_NOTES_{tag}.md").is_file())

    def test_packaged_plugin_ships_its_pinned_renderer_requirements(self):
        root_requirements = (REPOSITORY_ROOT / "requirements.txt").read_bytes()
        packaged_requirements = PLUGIN_ROOT / "requirements.txt"
        self.assertTrue(packaged_requirements.is_file())
        self.assertEqual(
            packaged_requirements.read_text(encoding="utf-8").replace("\r\n", "\n"),
            root_requirements.decode("utf-8").replace("\r\n", "\n"),
        )

    def test_blog_references_match_the_executable_five_to_seven_section_contract(self):
        schema = BLOG_SCHEMA.read_text(encoding="utf-8")
        policy = BLOG_POLICY.read_text(encoding="utf-8")
        self.assertIn("five to seven ordered sections", schema)
        self.assertIn("five to seven topic-specific sections", policy)
        self.assertNotIn("three to seven", schema.lower())
        self.assertNotIn("three to seven", policy.lower())
        for required_field in [
            '"lead_evidence_refs"',
            '"evidence_refs"',
            '"evidence_id"',
            '"first_person_evidence_refs"',
            '"disclosure": "AI 생성 설명 이미지"',
        ]:
            self.assertIn(required_field, schema)
        self.assertIn("raw Markdown lists", schema)
        self.assertIn("fenced code blocks", schema)

    def test_default_prompt_routes_only_the_action_requested_by_the_user(self):
        metadata = OPENAI_YAML.read_text(encoding="utf-8")
        prompt = next(
            line.split(":", 1)[1].strip().strip('"')
            for line in metadata.splitlines()
            if line.startswith("  default_prompt:")
        )
        self.assertIn("$obsidian-manuscript-publisher", metadata)
        self.assertLessEqual(len(prompt), 128)
        self.assertIn("저장하거나", prompt)
        self.assertIn("A4·블로그·맞춤 출력", prompt)

    def test_skill_requires_blog_source_references_to_resolve_in_the_active_bundle(self):
        skill = SKILL.read_text(encoding="utf-8")
        for required_text in [
            "active conversation bundle",
            "turn IDs and attachment or file entries",
            "unresolved source_refs",
        ]:
            self.assertIn(required_text, skill)

    def test_blog_references_describe_manual_editorial_attestation_without_semantic_overclaim(self):
        schema = BLOG_SCHEMA.read_text(encoding="utf-8")
        policy = BLOG_POLICY.read_text(encoding="utf-8")
        for document in (schema, policy):
            self.assertIn("manual editorial attestation", document)
            self.assertIn("does not independently prove semantic source grounding", document)

    def test_book_publication_contract_documents_exact_preflight_and_non_destructive_failure(self):
        skill = SKILL.read_text(encoding="utf-8")
        schema = BOOK_SCHEMA.read_text(encoding="utf-8")
        policy = ASSET_POLICY.read_text(encoding="utf-8")
        self.assertIn('"output_profile": "book_a4"', schema)
        self.assertIn('"source_markdown"', schema)
        self.assertIn('"validated_inputs"', schema)
        self.assertIn("exact publication allowlist", skill)
        self.assertIn("snapshot every allowed file before the first REST request", skill)
        self.assertIn("Never delete or roll back remote files automatically", skill)
        self.assertIn("fresh immutable version", skill)
        self.assertNotIn("rollback_conflicts", skill)
        self.assertNotIn("remote_content_changed", skill)
        self.assertIn("manifest-listed assets", policy)

    def test_skill_exports_only_after_ready_validation_and_render(self):
        skill = SKILL.read_text(encoding="utf-8")
        for required_text in [
            "scripts/export_publication_bundle.py",
            "status: ready",
            "validation → render → Vault publication attempt → desktop export",
        ]:
            self.assertIn(required_text, skill)
        self.assertLess(
            skill.index("status: ready"),
            skill.index("scripts/export_publication_bundle.py"),
        )
        self.assertLess(
            skill.index("render_manuscript.py"),
            skill.index("scripts/export_publication_bundle.py"),
        )

    def test_skill_reports_vault_and_desktop_outcomes_separately(self):
        skill = SKILL.read_text(encoding="utf-8")
        for required_text in [
            "vault_publication_status",
            "desktop_export_status",
            "A Vault REST failure does not block desktop export",
        ]:
            self.assertIn(required_text, skill)

    def test_skill_routes_reexport_and_backfill_without_implicit_history_scan(self):
        skill = SKILL.read_text(encoding="utf-8")
        reference = PUBLICATION_LIBRARY.read_text(encoding="utf-8") if PUBLICATION_LIBRARY.is_file() else ""
        combined = skill + "\n" + reference
        for required_text in [
            "바탕화면 출판함만 다시 만들어줘",
            "v0.N 검증본을 출판함에 정리해줘",
            "exact project, profile, and version",
            "Never scan all historical versions implicitly",
        ]:
            self.assertIn(required_text, combined)

    def test_publication_library_reference_defines_copy_ready_bundle_and_cli(self):
        self.assertTrue(PUBLICATION_LIBRARY.is_file())
        reference = PUBLICATION_LIBRARY.read_text(encoding="utf-8")
        for required_text in [
            "01 본문-복사용.txt",
            "02 원고.md",
            "02 블로그.md",
            "03 미리보기.html",
            "05 이미지-삽입순서.md",
            "_meta/export-manifest.json",
            "--source-version-dir",
            "--publication-root",
            "--project-destination-root",
            "--vault-path",
            "already_exported",
            "history_exported",
            "immutable_export_conflict",
        ]:
            self.assertIn(required_text, reference)

    def test_book_and_blog_schemas_define_separate_desktop_bundles(self):
        book_schema = BOOK_SCHEMA.read_text(encoding="utf-8")
        blog_schema = BLOG_SCHEMA.read_text(encoding="utf-8")
        for required_text in [
            "book_a4 desktop bundle",
            "04 인쇄용.pdf",
            "05 이미지-삽입순서.md",
        ]:
            self.assertIn(required_text, book_schema)
        for required_text in [
            "adaptive_blog desktop bundle",
            "04 이미지-삽입순서.md",
            "adaptive_blog desktop bundle never contains a PDF",
        ]:
            self.assertIn(required_text, blog_schema)

    def test_readme_teaches_the_beginner_copy_image_preview_and_history_workflow(self):
        readme = README.read_text(encoding="utf-8")
        for required_text in [
            "<Windows 바탕화면>\\옵시디언 원고",
            "01 본문-복사용.txt",
            "images",
            "이미지-삽입순서.md",
            "00 최신본",
            "99 이전버전",
            "네이버·티스토리·워드프레스에 자동 게시하지 않습니다",
            "Reset all crypto",
            "Re-generate certificates",
        ]:
            self.assertIn(required_text, readme)

    def test_agent_metadata_mentions_verified_desktop_publication_bundles(self):
        metadata = OPENAI_YAML.read_text(encoding="utf-8")
        prompt = next(
            line.split(":", 1)[1].strip().strip('"')
            for line in metadata.splitlines()
            if line.startswith("  default_prompt:")
        )
        self.assertLessEqual(len(prompt), 128)
        self.assertIn("Obsidian", prompt)
        self.assertIn("발행해 줘", prompt)


if __name__ == "__main__":
    unittest.main()
