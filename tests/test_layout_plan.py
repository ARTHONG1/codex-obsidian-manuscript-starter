import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/layout_plan.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("layout_plan", SCRIPT)
layout_plan = importlib.util.module_from_spec(SPEC)
try:
    sys.modules["layout_plan"] = layout_plan
    SPEC.loader.exec_module(layout_plan)
except FileNotFoundError:
    layout_plan = None


class LayoutPlanTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(layout_plan, "layout_plan.py must exist")

    def test_unknown_component_and_raw_url_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "custom_layout_contract_invalid"):
            layout_plan.compile_layout_plan({"title": "x", "blocks": [{"id": "one", "component": "script"}]})
        with self.assertRaisesRegex(ValueError, "custom_layout_contract_invalid"):
            layout_plan.compile_layout_plan({"title": "x", "blocks": [{"id": "one", "component": "title", "text": "https://example.com"}]})

    def test_plan_has_unique_ordered_ids_and_canonical_serialization(self):
        data = {"title": "원고", "blocks": [{"id": "title", "component": "title", "text": "제목"}, {"id": "body", "component": "paragraphs", "text": "본문"}]}
        plan = layout_plan.compile_layout_plan(data)
        self.assertEqual(plan.block_ids, ("title", "body"))
        self.assertEqual(plan.canonical_json(), layout_plan.compile_layout_plan(data).canonical_json())
        self.assertIn("title", plan.canonical_json())

    def test_duplicate_ids_and_unbounded_style_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "custom_layout_contract_invalid"):
            layout_plan.compile_layout_plan({"blocks": [{"id": "same", "component": "title"}, {"id": "same", "component": "paragraphs"}]})
        with self.assertRaisesRegex(ValueError, "custom_layout_contract_invalid"):
            layout_plan.compile_layout_plan({"blocks": [{"id": "one", "component": "title", "font_size": 999}]})


if __name__ == "__main__":
    unittest.main()
