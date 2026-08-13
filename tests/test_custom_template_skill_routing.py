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

    def test_existing_profiles_and_delete_contract_remain(self):
        for term in ("book_a4", "adaptive_blog", "Delete Current Conversation Bundle", "Local REST API"):
            self.assertIn(term, self.text)


if __name__ == "__main__":
    unittest.main()
