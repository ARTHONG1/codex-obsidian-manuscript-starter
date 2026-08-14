import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts"
import sys
sys.path.insert(0, str(SCRIPTS))
from template_candidate_state import activate_candidate, approve_candidate
spec = importlib.util.spec_from_file_location("register_custom_template", SCRIPTS / "register_custom_template.py")
registration = importlib.util.module_from_spec(spec)
sys.modules["register_custom_template"] = registration
spec.loader.exec_module(registration)


class FakeRest:
    def __init__(self):
        self.files = {}
        self.writes = []

    def list(self, _config, directory, _base_url=None):
        prefix = directory.rstrip("/") + "/"
        names = []
        for path in self.files:
            if path.startswith(prefix):
                names.append(path[len(prefix):].split("/", 1)[0])
        return sorted(set(names)) or None

    def save(self, _config, path, content, _base_url=None):
        self.files[path] = bytes(content)
        self.writes.append(path)
        return path

    def read(self, _config, path, _base_url=None):
        return self.files.get(path)


class RegistrationTests(unittest.TestCase):
    def candidate(self, root: Path, status="preview_ready") -> Path:
        candidate = root / "candidate"
        candidate.mkdir()
        for name, content in {
            "template.json": {"candidate_id": "c-one", "display_name": "A"},
            "source-manifest.json": {"sources": []},
            "source-analysis.json": {"status": "safe_for_preview"},
            "preview-content.json": {"marker": "preview"},
        }.items():
            (candidate / name).write_text(json.dumps(content), encoding="utf-8")
        return candidate

    def test_requires_exact_candidate_and_preview_ready(self):
        with self.assertRaisesRegex(ValueError, "template_preview_not_ready"):
            registration.register_candidate({}, Path("candidate"), {"candidate_id": "c-one", "approved_candidate_id": "c-one", "status": "needs_review"}, transport=FakeRest())

    def test_allocates_immutable_template_version_and_reads_back_every_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = self.candidate(root)
            fake = FakeRest()
            with patch.dict("os.environ", {"CODEX_OBSIDIAN_STATE_ROOT": str(root / "state")}):
                activate_candidate("conversation-1", "c-one", "v-one", root / "state")
                approve_candidate("conversation-1", "c-one", "v-one", root / "state")
                approval = {"candidate_id": "c-one", "approved_candidate_id": "c-one", "conversation_key": "conversation-1", "validation_hash": "v-one", "status": "preview_ready"}
                result = registration.register_candidate({}, candidate, approval, transport=fake)
            self.assertEqual(result["version"], "t0.1")
            self.assertTrue(all(path.startswith("_system/manuscript-template-registry/c-one/t0.1/") for path in fake.writes))
            self.assertIn("_system/manuscript-template-registry/c-one/t0.1/registry.json", fake.files)

    def test_local_registry_root_is_not_accepted_as_a_vault_write_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "registration_requires_local_rest"):
                registration.register_candidate({}, Path(directory), {"candidate_id": "c-one", "approved_candidate_id": "c-one", "status": "preview_ready"})


if __name__ == "__main__":
    unittest.main()
