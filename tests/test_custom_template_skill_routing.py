import unittest
from pathlib import Path


SKILL = Path(__file__).parents[1] / "plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/SKILL.md"


class CustomTemplateSkillRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SKILL.read_text(encoding="utf-8")

    def test_custom_profile_is_explicit_and_approval_gated(self):
        self.assertIn("custom_manuscript", self.text)
        self.assertIn("preview_ready", self.text)
        self.assertIn("candidate ID", self.text)

    def test_supported_profiles_and_delete_contract_remain(self):
        for term in ("custom_manuscript", "adaptive_blog", "Delete Current Conversation Bundle", "Local REST API"):
            self.assertIn(term, self.text)

    def test_generic_manuscript_request_requires_registered_template_selection(self):
        routes = [line for line in self.text.splitlines() if "원고를 만들어줘" in line]
        self.assertTrue(routes, "The generic manuscript trigger must have a documented route")
        for route in routes:
            self.assertNotIn("(references/adaptive-blog-workflow.md)", route)
            self.assertRegex(route, r"(?i)(?:without|no)[^.\n]*(?:selected|registered|approved)[^.\n]*template")
            self.assertRegex(route, r"(?i)ask[^.\n]*(?:approved|registered)[^.\n]*(?:user|custom) template")
            self.assertRegex(route, r"(?i)(?:do not|never)[^.\n]*(?:silently|automatically)[^.\n]*blog")
        self.assertIn("(references/custom-manuscript-workflow.md)", self.text)
        self.assertNotRegex(
            self.text,
            r"(?i)`?book_a4`? (?:is|remains) the default",
        )


if __name__ == "__main__":
    unittest.main()
