from pathlib import Path
import json
import unittest


SKILL = Path(__file__).resolve().parents[1] / "plugins" / "obsidian-manuscript-publisher" / "skills" / "obsidian-manuscript-publisher" / "SKILL.md"


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


if __name__ == "__main__":
    unittest.main()
