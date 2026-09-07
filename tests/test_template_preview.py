import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts"
sys.path.insert(0, str(SCRIPTS))


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


validator = renderer = None
try:
    validator = load("validate_template_candidate")
    renderer = load("render_template_preview")
except FileNotFoundError:
    pass


class TemplatePreviewTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(validator, "candidate validator must exist")

    def test_safe_needs_review_can_preview_but_cannot_register(self):
        candidate = {"status": "needs_review", "safe_for_preview": True, "critical_unresolved": ["page_size"]}
        result = validator.validate_candidate(candidate)
        self.assertTrue(result["safe_for_preview"])
        self.assertEqual(result["status"], "needs_review")
        self.assertFalse(result["registration_ready"])

    def test_preview_contains_neutral_marker_and_no_source_text(self):
        with tempfile.TemporaryDirectory() as directory:
            result = renderer.render_preview({"display_name": "A", "candidate_id": "c-one", "blocks": [{"component": "title"}]}, directory)
            html = Path(result["html"]).read_text(encoding="utf-8")
            self.assertIn("템플릿 검토용 미리보기", html)
            self.assertNotIn("C:\\", html)


if __name__ == "__main__":
    unittest.main()
