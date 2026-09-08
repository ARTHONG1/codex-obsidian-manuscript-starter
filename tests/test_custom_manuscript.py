import importlib.util
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from pypdf import PdfReader

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
            from pypdf import PdfReader
            text = "\n".join(page.extract_text() or "" for page in PdfReader(package["pdf"]).pages)
            self.assertIn("본문입니다", text)
            self.assertGreater(len(PdfReader(package["pdf"]).pages), 0)

    def test_does_not_accept_raw_markup_as_content(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                custom.render_custom_manuscript({"title": "주제", "blocks": [{"component": "paragraphs", "text": "<script>x</script>"}]}, directory)

    def image_fixture(self, root):
        path = root / "source.png"
        Image.new("RGB", (80, 40), "red").save(path)
        return {"title": "Synthetic", "assets": [{"id": "figure", "path": "source.png", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}],
                "blocks": [{"id": "before", "component": "paragraphs", "text": "Before"},
                           {"id": "picture", "component": "image", "asset_id": "figure", "alt": "Red rectangle", "caption": "Figure caption"},
                           {"id": "after", "component": "paragraphs", "text": "After"}]}

    def test_image_is_embedded_in_pdf_and_linked_with_caption_in_html_and_markdown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = self.image_fixture(root)
            result = custom.render_custom_manuscript(data, root / "out", asset_root=root)
            self.assertEqual(len(result["assets"]), 1)
            copied = Path(result["assets"][0])
            self.assertEqual(copied.read_bytes(), (root / "source.png").read_bytes())
            relative = copied.relative_to(root / "out").as_posix()
            markdown = Path(result["markdown"]).read_text(encoding="utf-8")
            html_text = Path(result["html"]).read_text(encoding="utf-8")
            self.assertIn(f"![Red rectangle]({relative})", markdown)
            self.assertIn(f"src='{relative}'", html_text)
            self.assertIn("<figcaption>Figure caption</figcaption>", html_text)
            for rendered in (markdown, html_text):
                self.assertLess(rendered.index("Before"), rendered.index("Figure caption"))
                self.assertLess(rendered.index("Figure caption"), rendered.index("After"))
            pdf = PdfReader(result["pdf"])
            self.assertEqual(sum(len(page.images) for page in pdf.pages), 1)
            self.assertEqual(pdf.pages[0].images[0].image.size, (80, 40))
            text = "\n".join(page.extract_text() for page in pdf.pages)
            self.assertLess(text.index("Before"), text.index("Figure caption"))
            self.assertLess(text.index("Figure caption"), text.index("After"))
            self.assertEqual([b["id"] for b in json.loads(result["layout_plan"])["blocks"]], ["before", "picture", "after"])

    def test_unsafe_or_missing_assets_are_rejected_before_creating_output(self):
        for case in ("no_root", "missing", "tampered", "unknown", "../source.png", "/source.png", "C:/source.png", "https://example.com/x.png", "nested\\source.png", "bad_image"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                data = self.image_fixture(root)
                if case == "missing":
                    (root / "source.png").unlink()
                elif case == "tampered":
                    (root / "source.png").write_bytes(b"tampered")
                elif case == "unknown":
                    data["blocks"][1]["asset_id"] = "absent"
                elif case == "bad_image":
                    (root / "source.png").write_bytes(b"not an image")
                    data["assets"][0]["sha256"] = hashlib.sha256(b"not an image").hexdigest()
                elif case != "no_root":
                    data["assets"][0]["path"] = case
                kwargs = {} if case == "no_root" else {"asset_root": root}
                with self.assertRaises(ValueError):
                    custom.render_custom_manuscript(data, root / "out", **kwargs)
                self.assertFalse((root / "out").exists())

    def test_quick_table_renders_cells_in_all_formats_on_narrow_page(self):
        with tempfile.TemporaryDirectory() as directory:
            result = custom.render_custom_manuscript({"title": "Table", "page_tokens": {"width": 320, "height": 600, "margin": 32}, "blocks": [
                {"component": "quick_table", "headers": ["Name", "Value"], "rows": [["Alpha", "One"], ["Beta", "Two"]]},
                {"component": "tip_box", "text": "Narrow box"}]}, directory)
            self.assertIn("| Name | Value |\n| --- | --- |\n| Alpha | One |", Path(result["markdown"]).read_text(encoding="utf-8"))
            self.assertIn("<td>Alpha</td>", Path(result["html"]).read_text(encoding="utf-8"))
            pdf = PdfReader(result["pdf"])
            self.assertEqual(float(pdf.pages[0].mediabox.width), 240)
            self.assertIn("Alpha", pdf.pages[0].extract_text())
            import pdfplumber
            with pdfplumber.open(result["pdf"]) as document:
                for page in document.pages:
                    for drawing in page.edges:
                        self.assertGreaterEqual(drawing["x0"], 24)
                        self.assertLessEqual(drawing["x1"], 216)

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "manuscript.html").write_bytes(b"keep")
            with self.assertRaises(ValueError):
                custom.render_custom_manuscript({"title": "Test", "blocks": []}, root)
            self.assertEqual({p.name: p.read_bytes() for p in root.iterdir()}, {"manuscript.html": b"keep"})

    def test_two_fresh_renders_have_identical_pdf_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = self.image_fixture(root)
            first = custom.render_custom_manuscript(data, root / "first", asset_root=root)
            second = custom.render_custom_manuscript(data, root / "second", asset_root=root)
            self.assertEqual(Path(first["pdf"]).read_bytes(), Path(second["pdf"]).read_bytes())

    def test_nine_distinct_images_and_repeated_reference_render_in_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = {"title": "Nine steps", "assets": [], "blocks": []}
            for index in range(9):
                path = root / f"step-{index}.png"
                Image.new("RGB", (8, 8), (index * 20, 0, 0)).save(path)
                data["assets"].append({"id": f"step-{index}", "path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
                data["blocks"].append({"component": "image", "asset_id": f"step-{index}", "caption": f"Step {index}"})
            data["blocks"].append({"component": "image", "asset_id": "step-0", "caption": "Repeated step"})
            result = custom.render_custom_manuscript(data, root / "out", asset_root=root)
            self.assertEqual(len(result["assets"]), 9)
            self.assertEqual(Path(result["html"]).read_text(encoding="utf-8").count("<img "), 10)
            self.assertEqual(Path(result["markdown"]).read_text(encoding="utf-8").count("![]("), 10)
            text = "\n".join(p.extract_text() for p in PdfReader(result["pdf"]).pages)
            self.assertLess(text.index("Step 8"), text.index("Repeated step"))

    def test_more_than_64_asset_records_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = self.image_fixture(root)
            data["assets"] = [{**data["assets"][0], "id": f"asset-{i}"} for i in range(65)]
            data["blocks"] = []
            with self.assertRaises(ValueError):
                custom.render_custom_manuscript(data, root / "out", asset_root=root)
            self.assertFalse((root / "out").exists())

    def test_unused_manifest_assets_are_rejected_before_output(self):
        for include_used in (False, True):
            with self.subTest(include_used=include_used), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                data = self.image_fixture(root)
                if include_used:
                    extra = root / "unintended.png"
                    Image.new("RGB", (8, 8), "blue").save(extra)
                    data["assets"].append({"id": "unused", "path": extra.name, "sha256": hashlib.sha256(extra.read_bytes()).hexdigest()})
                else:
                    data["blocks"] = []
                with self.assertRaisesRegex(ValueError, "custom_asset_unreferenced"):
                    custom.render_custom_manuscript(data, root / "out", asset_root=root)
                self.assertFalse((root / "out").exists())

    def test_tall_image_and_wrapped_caption_share_a_pdf_page(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = self.image_fixture(root)
            Image.new("RGB", (100, 2000), "red").save(root / "source.png")
            data["assets"][0]["sha256"] = hashlib.sha256((root / "source.png").read_bytes()).hexdigest()
            data["page_tokens"] = {"width": 320, "height": 400, "margin": 32}
            data["blocks"][1]["caption"] = "Tall figure caption " * 8
            result = custom.render_custom_manuscript(data, root / "out", asset_root=root)
            reader = PdfReader(result["pdf"])
            picture_pages = [i for i, page in enumerate(reader.pages) if len(page.images)]
            caption_pages = [i for i, page in enumerate(reader.pages) if "Tall figure caption" in page.extract_text()]
            self.assertEqual(picture_pages, caption_pages)
            import pdfplumber
            with pdfplumber.open(result["pdf"]) as document:
                page = document.pages[picture_pages[0]]
                words = [w for w in page.extract_words() if w["text"] == "Tall"]
                self.assertGreaterEqual(words[0]["top"], page.images[0]["bottom"])
                self.assertLess(words[0]["top"] - page.images[0]["bottom"], 20)

    def test_title_caption_and_alt_cannot_inject_markup_or_urls(self):
        for field in ("title", "caption", "alt"):
            for value in ("<script>x</script>", "https://example.com/image.png", 42):
                with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    data = self.image_fixture(root)
                    (data if field == "title" else data["blocks"][1])[field] = value
                    with self.assertRaises(ValueError):
                        custom.render_custom_manuscript(data, root / "out", asset_root=root)
                    self.assertFalse((root / "out").exists())

    def test_title_and_caption_markdown_image_syntax_is_literal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = self.image_fixture(root)
            data["title"] = "![unverified](/outside.png)"
            data["blocks"][1]["caption"] = "![caption](/outside.png)"
            result = custom.render_custom_manuscript(data, root / "out", asset_root=root)
            markdown = Path(result["markdown"]).read_text(encoding="utf-8")
            self.assertNotIn("![unverified]", markdown)
            self.assertNotIn("![caption]", markdown)

    def test_failed_pdf_rolls_back_new_output_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = self.image_fixture(root)
            # PDF generation is the failure boundary; asset validation and writes remain real.
            with patch.object(custom, "_pdf", side_effect=RuntimeError("PDF failure")):
                with self.assertRaises(RuntimeError):
                    custom.render_custom_manuscript(data, root / "out", asset_root=root)
            self.assertEqual(sorted(p.name for p in root.iterdir()), ["source.png"])

    def test_promotion_failure_rolls_back_only_our_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = self.image_fixture(root)
            output = root / "out"
            output.mkdir()
            (output / "unrelated.txt").write_bytes(b"keep")
            original = custom.shutil.copyfileobj
            calls = 0

            def fail_last_copy(source, destination, *args):
                nonlocal calls
                calls += 1
                if calls == 4:
                    destination.write(b"partial")
                    raise OSError("disk full")
                return original(source, destination, *args)

            with patch.object(custom.shutil, "copyfileobj", side_effect=fail_last_copy):
                with self.assertRaisesRegex(OSError, "disk full"):
                    custom.render_custom_manuscript(data, output, asset_root=root)
            self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, {"unrelated.txt": b"keep"})

    def test_asset_pixel_byte_and_manifest_limits_are_enforced(self):
        import custom_assets
        for limit in ("MAX_PIXELS", "MAX_ASSET_BYTES", "MAX_TOTAL_BYTES", "MAX_ASSETS"):
            with self.subTest(limit=limit), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                data = self.image_fixture(root)
                with patch.object(custom_assets, limit, 0), self.assertRaises(ValueError):
                    custom.render_custom_manuscript(data, root / "out", asset_root=root)
                self.assertFalse((root / "out").exists())

    def test_reparse_asset_or_output_ancestor_is_rejected(self):
        import stat
        from types import SimpleNamespace
        for target in ("source.png", "out"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                data = self.image_fixture(root)
                original = Path.lstat

                def reparse_info(path, *args, **kwargs):
                    if path == root / target:
                        return SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=0x400)
                    return original(path, *args, **kwargs)

                with patch.object(Path, "lstat", reparse_info), self.assertRaises(ValueError):
                    custom.render_custom_manuscript(data, root / "out", asset_root=root)
                self.assertFalse((root / "out").exists())

    def test_duplicate_asset_ids_and_wrong_format_are_rejected(self):
        for case in ("duplicate", "format", "animation"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                data = self.image_fixture(root)
                if case == "duplicate":
                    data["assets"].append(dict(data["assets"][0]))
                elif case == "format":
                    (root / "source.png").rename(root / "source.jpg")
                    data["assets"][0]["path"] = "source.jpg"
                else:
                    Image.new("RGB", (80, 40), "red").save(root / "source.png", save_all=True, append_images=[Image.new("RGB", (80, 40), "blue")])
                    data["assets"][0]["sha256"] = hashlib.sha256((root / "source.png").read_bytes()).hexdigest()
                with self.assertRaises(ValueError):
                    custom.render_custom_manuscript(data, root / "out", asset_root=root)
                self.assertFalse((root / "out").exists())


if __name__ == "__main__":
    unittest.main()
