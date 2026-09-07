import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/editorial_quality.py"
spec = importlib.util.spec_from_file_location("editorial_quality", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class EditorialQualityV3Tests(unittest.TestCase):
    def test_sentence_count_and_range(self):
        self.assertEqual(module.sentence_count("첫 문장입니다. 둘째 문장입니다."), 2)
        self.assertEqual(module.validate_sentence_range("하나입니다.", 2, 4, "step_sentence_range_invalid")[0]["code"], "step_sentence_range_invalid")

    def test_voice_rejects_absolute_promotion(self):
        self.assertTrue(module.validate_master_voice("한 번에 완벽하게 끝납니다."))

    def test_visual_brief_requires_overlay_prohibition(self):
        brief = {"purpose": "result", "screen_state": "ready", "visible_elements": ["table"], "reader_check": "check", "style": "editorial", "forbidden_overlays": ["red_box", "numbered_callout", "arrow"]}
        self.assertEqual(module.validate_visual_brief(brief, asset_id="a1"), [])

    def test_score_blocks_below_85(self):
        score, issues = module.compute_editorial_score({"structure": 20, "specificity": 20, "voice": 15, "reproducibility": 15, "visuals": 10, "practice": 5, "safety": 5, "no_unverified_claims": True, "no_sensitive_data": True, "visuals_reviewed": True})
        self.assertEqual(score, 90)
        self.assertFalse(issues)


if __name__ == "__main__":
    unittest.main()
