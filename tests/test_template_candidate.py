import importlib.util
import json
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


template_candidate = None
try:
    template_candidate = load("build_template_candidate")
except FileNotFoundError:
    pass


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(template_candidate, "build_template_candidate.py must exist")

    def test_builds_neutral_candidate_with_source_hashes_only(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "example.png"
            source.write_bytes(b"\x89PNG\r\n\x1a\nsource bytes")
            evidence = {"source_refs": [{"file_id": "source-1", "page": 1}], "sections": []}
            result = template_candidate.build_candidate("출판사 A", [source], evidence, Path(directory) / "candidate")
            self.assertTrue(result["candidate_id"].startswith("c-"))
            payload = json.loads((Path(directory) / "candidate" / "template.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "candidate")
            self.assertNotIn("source bytes", (Path(directory) / "candidate").read_text(encoding="utf-8") if False else json.dumps(payload))
            self.assertFalse((Path(directory) / "candidate" / "example.png").exists())

    def test_approval_is_required_before_registration(self):
        with self.assertRaises(template_candidate.TemplateCandidateError) as context:
            template_candidate.require_approval({"candidate_id": "c-one", "approved_candidate_id": "c-two"})
        self.assertEqual(str(context.exception), "template_approval_required")


if __name__ == "__main__":
    unittest.main()
