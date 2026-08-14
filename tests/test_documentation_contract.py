from pathlib import Path
import json
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_MANIFEST = ROOT / "plugins/obsidian-manuscript-publisher/.codex-plugin/plugin.json"
MARKETPLACE = ROOT / ".agents/plugins/marketplace.json"
OPENAI_AGENT = ROOT / "plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/agents/openai.yaml"
README = (ROOT / "README.md").read_text(encoding="utf-8")
INSTALL_GUIDE = (ROOT / "docs/INSTALL_GUIDE.md").read_text(encoding="utf-8")
RELEASE = (ROOT / "docs/RELEASE.md").read_text(encoding="utf-8")
TROUBLESHOOTING = (ROOT / "docs/TROUBLESHOOTING.md").read_text(encoding="utf-8")
ALL_TESTS_RUNNER = (ROOT / "ci/run-all-tests.ps1").read_text(encoding="utf-8")
SKILL = (ROOT / "plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/SKILL.md").read_text(encoding="utf-8")
BLOG_SCHEMA = (ROOT / "plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/blog-schema.md").read_text(encoding="utf-8")
ASSET_POLICY = (ROOT / "plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/asset-policy.md").read_text(encoding="utf-8")
EDITORIAL_PROFILE = (ROOT / "plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/master-editorial-profile.md").read_text(encoding="utf-8") if (ROOT / "plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/master-editorial-profile.md").exists() else ""


class DocumentationContractTests(unittest.TestCase):
    WORKFLOW_REFERENCES = (
        "conversation-workflow.md",
        "book-a4-workflow.md",
        "adaptive-blog-workflow.md",
        "custom-manuscript-workflow.md",
        "deletion-workflow.md",
        "legacy-book-contracts.md",
    )

    def test_skill_is_progressively_disclosed_router(self):
        lines = [line for line in SKILL.splitlines() if line.strip()]
        self.assertLessEqual(len(lines), 180)
        for reference in self.WORKFLOW_REFERENCES:
            self.assertIn(reference, SKILL)
        self.assertIn("master-editorial-profile.md", SKILL)
        self.assertIn("publication-library.md", SKILL)

    def test_skill_routes_every_public_trigger_to_a_direct_reference(self):
        routes = {
            "이 프로젝트를 원고 프로젝트로 등록해줘": "conversation-workflow.md",
            "이 대화 전체를 옵시디언에 저장해줘": "conversation-workflow.md",
            "이 대화 원고 재료 최신화해줘": "conversation-workflow.md",
            "이 대화의 옵시디언 자료를 전부 삭제해줘": "deletion-workflow.md",
            "출판 원고형": "book-a4-workflow.md",
            "범용 블로그형": "adaptive-blog-workflow.md",
            "출판사 A 원고형": "custom-manuscript-workflow.md",
            "기존 양식": "legacy-book-contracts.md",
            "레거시 양식": "legacy-book-contracts.md",
            "V1": "legacy-book-contracts.md",
            "V2": "legacy-book-contracts.md",
            "바탕화면 출판함만 다시 만들어줘": "publication-library.md",
        }
        for trigger, reference in routes.items():
            self.assertIn(trigger, SKILL)
            self.assertLess(
                SKILL.index(trigger),
                SKILL.index(reference),
                msg=f"{trigger!r} must route directly to {reference}",
            )

    def test_router_declares_v3_default_once_and_isolates_legacy_formulas(self):
        self.assertEqual(len(re.findall(r"template_version:\s*3", SKILL)), 1)
        self.assertNotRegex(SKILL, r"N Steps require exactly N-1 tips")
        self.assertNotRegex(SKILL, r"Each V2 Step body contains exactly two or three sentences")

    def test_router_keeps_forward_pressure_safety_prohibitions(self):
        for prohibition in (
            "Never scan all Codex conversations",
            "Never overwrite a finished version",
            "Never call unverified output complete",
            "Never delete during archive, refresh, synthesis, render, or publish",
            "Do not use direct filesystem writes",
            "never send a Local REST API key",
        ):
            self.assertIn(prohibition, SKILL)

    def test_plugin_default_prompt_contract(self):
        manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
        prompts = manifest["interface"]["defaultPrompt"]
        self.assertIsInstance(prompts, list)
        self.assertLessEqual(len(prompts), 3)
        self.assertTrue(all(isinstance(value, str) and 0 < len(value) <= 128 for value in prompts))

    def test_local_marketplace_source_contains_only_source_and_path(self):
        marketplace = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
        source = marketplace["plugins"][0]["source"]
        self.assertEqual(set(source), {"source", "path"})

    def test_openai_default_prompt_is_short_and_aligned(self):
        prompt_line = next(
            line for line in OPENAI_AGENT.read_text(encoding="utf-8").splitlines()
            if line.startswith("  default_prompt:")
        )
        prompt = prompt_line.split(":", 1)[1].strip().strip('"')
        self.assertLessEqual(len(prompt), 128)
        self.assertIn("Obsidian", prompt)

    def test_readme_lists_reproducible_python_and_pester_commands(self):
        self.assertIn("Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force", README)
        self.assertIn(".\\ci\\run-python-tests.ps1 -PythonPath $Python312", README)
        self.assertIn(".\\ci\\run-pester-tests.ps1", README)
        self.assertIn(".\\ci\\run-all-tests.ps1 -PythonPath $Python312", README)

    def test_aggregate_runner_self_inclusion_and_skip_inventory_are_documented(self):
        self.assertIn("tests\\TestRunnerContract.Tests.ps1", ALL_TESTS_RUNNER)
        self.assertIn("-ExpectedPythonSkipCount 4", README)
        self.assertIn("-ExpectedPythonSkipCount 4", INSTALL_GUIDE)
        self.assertIn("-ExpectedPythonSkipCount 4", RELEASE)
        self.assertIn("-ExpectedPythonSkipCount 4", TROUBLESHOOTING)
        for test_name in (
            "test_real_wheelhouse_recreates_committed_lock_when_provided",
            "test_existing_item_reparse_point_is_rejected_when_supported",
            "test_rejects_reparse_point_without_following_it_when_supported",
            "test_snapshot_rejects_reparse_staging_parent_when_supported",
        ):
            self.assertIn(test_name, RELEASE)
            self.assertIn(test_name, TROUBLESHOOTING)

    def test_docs_name_real_validators_and_not_nonexistent_ones(self):
        for document in (README, SKILL):
            self.assertNotIn("validate_publication.py", document)
            self.assertNotIn("validate_export.py", document)
        self.assertIn("validate_manuscript.py", SKILL)
        self.assertIn("validate_blog.py", SKILL)

    def test_docs_publish_the_complete_deterministic_error_code_contract(self):
        expected = {
            "blog_profile_required",
            "insufficient_evidence",
            "asset_hash_mismatch",
            "image_generation_failed",
            "validation_not_ready",
            "stale_validation",
            "unexpected_source_file",
            "unsafe_path",
            "immutable_export_conflict",
        }
        combined = SKILL + "\n" + BLOG_SCHEMA + "\n" + ASSET_POLICY
        for code in expected:
            self.assertIn(code, combined)

    def test_docs_define_the_exact_step_title_noun_allowlist(self):
        self.assertIn("exact noun allowlist", SKILL)
        for ending in ("준비", "분석", "설계", "구성", "구현", "연결", "설정", "생성", "검증", "수정", "테스트", "설치", "배포", "실행", "적용", "활용"):
            self.assertIn(ending, SKILL)
        self.assertIn("합니다", SKILL)
        self.assertIn("하기", SKILL)

    def test_continuity_docs_distinguish_counted_and_executed_records(self):
        progress = (ROOT / "docs/continuity-record.md").read_text(encoding="utf-8")
        self.assertIn("counted records", progress.lower())
        self.assertIn("executed records", progress.lower())
        self.assertIn("do not claim that those items were executed", progress.lower())

    def test_v3_shared_master_editorial_profile_is_normative(self):
        self.assertTrue(EDITORIAL_PROFILE)
        for phrase in ("2~4", "3~5", "85", "red_box", "numbered_callout", "arrow", "generated_scene", "editorial"):
            self.assertIn(phrase, EDITORIAL_PROFILE)
        self.assertIn("master-editorial-profile.md", SKILL)

    def test_v3_profile_does_not_require_mechanical_step_tip_formula(self):
        self.assertIn("\uC720\uB3D9\uC801", EDITORIAL_PROFILE)
        self.assertIn("Step \uC218", EDITORIAL_PROFILE)
        self.assertIn("\uAC01 Step \uC0AC\uC774\uC5D0 \uC790\uB3D9\uC73C\uB85C \uD301", EDITORIAL_PROFILE)


if __name__ == "__main__":
    unittest.main()
