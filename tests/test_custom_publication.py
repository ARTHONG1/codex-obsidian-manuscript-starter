import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("finalize_custom_publication", SCRIPTS / "finalize_custom_publication.py")
publication = importlib.util.module_from_spec(spec)
sys.modules["finalize_custom_publication"] = publication
spec.loader.exec_module(publication)


class CustomPublicationTests(unittest.TestCase):
    def test_exports_rendered_files_to_desktop_and_separates_vault_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = publication.finalize_custom_publication({"title": "주제", "blocks": []}, root / "v0.1", root / "desktop")
            self.assertEqual(result["vault_publication_status"], "not_attempted")
            self.assertEqual(result["desktop_export_status"], "exported")
            self.assertTrue((root / "desktop" / "manuscript.pdf").exists())


if __name__ == "__main__":
    unittest.main()
