import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/template_model.py"
SPEC = importlib.util.spec_from_file_location("template_model", SCRIPT)
template_model = importlib.util.module_from_spec(SPEC)
sys.modules["template_model"] = template_model
try:
    SPEC.loader.exec_module(template_model)
except FileNotFoundError:
    template_model = None


class TemplateModelTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(template_model, "template_model.py must exist")

    def test_rejects_raw_markup_and_unknown_components(self):
        with self.assertRaises(ValueError):
            template_model.Template.from_dict({"display_name": "x", "blocks": [{"component": "<script>"}]})

    def test_canonical_json_is_stable_and_has_no_absolute_path(self):
        value = template_model.Template.from_dict({
            "display_name": "출판사 A 원고형",
            "blocks": [{"component": "title", "section_id": "title"}],
        })
        first = value.canonical_json()
        second = template_model.Template.from_dict(value.to_dict()).canonical_json()
        self.assertEqual(first, second)
        self.assertNotIn("C:\\", first)

    def test_candidate_id_changes_when_template_changes(self):
        one = template_model.Template.from_dict({"display_name": "A", "blocks": []})
        two = template_model.Template.from_dict({"display_name": "B", "blocks": []})
        self.assertNotEqual(one.candidate_id(), two.candidate_id())


if __name__ == "__main__":
    unittest.main()
