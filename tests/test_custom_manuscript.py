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


custom = None
try:
    custom = load("render_custom_manuscript")
except FileNotFoundError:
    pass


class CustomManuscriptTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(custom, "render_custom_manuscript.py must exist")

    def test_renders_markdown_html_pdf_from_one_layout_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            package = custom.render_custom_manuscript({"title": "주제", "blocks": [{"component": "paragraphs", "text": "본문입니다."}]}, directory)
            for key in ("markdown", "html", "pdf"):
                self.assertTrue(Path(package[key]).is_file())
            self.assertIn("본문입니다.", Path(package["markdown"]).read_text(encoding="utf-8"))

    def test_does_not_accept_raw_markup_as_content(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                custom.render_custom_manuscript({"title": "주제", "blocks": [{"component": "paragraphs", "text": "<script>x</script>"}]}, directory)


if __name__ == "__main__":
    unittest.main()
