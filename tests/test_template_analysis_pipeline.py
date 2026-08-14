import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("analyze_template_sources", SCRIPTS / "analyze_template_sources.py")
analysis = importlib.util.module_from_spec(SPEC)
sys.modules["analyze_template_sources"] = analysis
SPEC.loader.exec_module(analysis)


class TemplateAnalysisPipelineTests(unittest.TestCase):
    def test_image_analysis_ignores_caller_supplied_fake_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "example.png"
            Image.new("RGB", (40, 20), "white").save(source)
            output = root / "candidate"
            result = analysis.analyze_sources([source], output_dir=output)
            self.assertEqual(result["status"], "safe_for_preview")
            self.assertEqual(result["evidence"][0]["evidence"]["width"], 40)
            self.assertTrue((output / "source-analysis.json").is_file())
            self.assertNotIn(str(source), json.dumps(result))

    def test_pdf_analysis_dispatches_to_pdf_extractor(self):
        from reportlab.pdfgen import canvas
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "example.pdf"
            pdf = canvas.Canvas(str(source))
            pdf.drawString(20, 20, "ignored source text")
            pdf.save()
            result = analysis.analyze_sources([source])
            self.assertEqual(result["evidence"][0]["evidence"]["page_count"], 1)
            self.assertNotIn("ignored source text", json.dumps(result))

    def test_docx_analysis_dispatches_to_docx_extractor(self):
        from docx import Document
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "example.docx"
            document = Document()
            document.add_paragraph("source prose must not be copied")
            document.save(source)
            result = analysis.analyze_sources([source])
            self.assertEqual(result["evidence"][0]["evidence"]["paragraph_count"], 1)
            self.assertNotIn("source prose must not be copied", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
