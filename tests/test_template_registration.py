import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts"
sys.path.insert(0, str(SCRIPTS))

spec = importlib.util.spec_from_file_location("register_custom_template", SCRIPTS / "register_custom_template.py")
registration = importlib.util.module_from_spec(spec)
try:
    sys.modules["register_custom_template"] = registration
    spec.loader.exec_module(registration)
except FileNotFoundError:
    registration = None


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(registration)

    def test_requires_exact_candidate_and_preview_ready(self):
        with self.assertRaises(ValueError) as ctx:
            registration.register_candidate({"candidate_id": "c-one", "approved_candidate_id": "c-one", "status": "needs_review"}, tempfile.mkdtemp())
        self.assertEqual(str(ctx.exception), "template_preview_not_ready")

    def test_allocates_immutable_template_version(self):
        with tempfile.TemporaryDirectory() as directory:
            result = registration.register_candidate({"candidate_id": "c-one", "approved_candidate_id": "c-one", "status": "preview_ready", "display_name": "A"}, directory)
            self.assertEqual(result["version"], "t0.1")
            self.assertTrue(Path(result["record"]).is_file())


if __name__ == "__main__":
    unittest.main()
