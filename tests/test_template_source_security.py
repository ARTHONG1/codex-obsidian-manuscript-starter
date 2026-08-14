import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).parents[1] / "plugins" / "obsidian-manuscript-publisher" / "skills" / "obsidian-manuscript-publisher" / "scripts"
SPEC = importlib.util.spec_from_file_location("template_source", SCRIPT_DIR / "template_source.py")
template_source = importlib.util.module_from_spec(SPEC)
try:
    sys.modules["template_source"] = template_source
    SPEC.loader.exec_module(template_source)
except FileNotFoundError:
    template_source = None


class TemplateSourceSecurityTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(template_source, "template_source.py must exist")

    def test_rejects_unsupported_and_macro_extensions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "example.docm").write_bytes(b"PK")
            (root / "example.doc").write_bytes(b"legacy")
            self.assertEqual(template_source.inspect_source(root / "example.docm").code, "unsupported_template_source")
            self.assertEqual(template_source.inspect_source(root / "example.doc").code, "unsupported_template_source")

    def test_rejects_source_above_per_file_limit_before_parsing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large.png"
            with path.open("wb") as stream:
                stream.truncate(template_source.MAX_SOURCE_BYTES + 1)
            result = template_source.inspect_source(path)
            self.assertEqual(result.code, "template_source_too_large")

    def test_canonical_manifest_does_not_expose_absolute_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example.png"
            path.write_bytes(b"not-a-real-image")
            result = template_source.inspect_source(path)
            self.assertEqual(result.code, "invalid_source_signature")
            self.assertNotIn(str(path), result.to_dict())

    def test_rejects_a_source_set_above_file_count_before_parsing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for index in range(template_source.MAX_SOURCE_FILES + 1):
                path = root / f"{index}.png"
                path.write_bytes(b"not-an-image")
                paths.append(path)
            result = template_source.inspect_source_set(paths)
            self.assertEqual(result["code"], "template_source_count_exceeded")
            self.assertNotIn(str(root), result)

    def test_source_set_manifest_is_deterministic_and_uses_aggregate_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "b.png"
            second = root / "a.png"
            first.write_bytes(b"\x89PNG\r\n\x1a\n" + b"b")
            second.write_bytes(b"\x89PNG\r\n\x1a\n" + b"a")
            result = template_source.inspect_source_set([first, second])
            self.assertEqual(result["code"], "source_set_ready")
            self.assertEqual([item["file_name"] for item in result["sources"]], ["a.png", "b.png"])

    def test_rejects_reparse_point_without_following_it_when_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.png"
            target.write_bytes(b"\x89PNG\r\n\x1a\n")
            link = root / "link.png"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink unavailable: {exc}")
            result = template_source.inspect_source(link)
            self.assertEqual(result.code, "unsafe_source_path")


if __name__ == "__main__":
    unittest.main()
