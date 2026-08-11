from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
SKILL = (ROOT / "plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/SKILL.md").read_text(encoding="utf-8")
BLOG_SCHEMA = (ROOT / "plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/blog-schema.md").read_text(encoding="utf-8")
ASSET_POLICY = (ROOT / "plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/asset-policy.md").read_text(encoding="utf-8")
EDITORIAL_PROFILE = (ROOT / "plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/master-editorial-profile.md").read_text(encoding="utf-8") if (ROOT / "plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/master-editorial-profile.md").exists() else ""


class DocumentationContractTests(unittest.TestCase):
    def test_readme_lists_reproducible_python_and_pester_commands(self):
        self.assertIn("Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force", README)
        self.assertIn("python -m unittest discover -s tests -t tests", README)
        self.assertIn("Invoke-Pester -Script .\\tests\\InstallerContract.Tests.ps1", README)
        self.assertIn("Invoke-Pester -Script .\\tests\\SecretScan.Tests.ps1", README)

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
