import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/template_candidate_state.py"
SPEC = importlib.util.spec_from_file_location("template_candidate_state", SCRIPT)
state = importlib.util.module_from_spec(SPEC)
try:
    SPEC.loader.exec_module(state)
except FileNotFoundError:
    state = None


class CandidateStateTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(state, "template_candidate_state.py must exist")

    def test_exact_candidate_and_validation_hash_are_required_for_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state.activate_candidate("conversation-1", "c-one", "v-one", root)
            with self.assertRaisesRegex(ValueError, "stale_candidate_approval"):
                state.approve_candidate("conversation-1", "c-two", "v-one", root)
            with self.assertRaisesRegex(ValueError, "stale_candidate_approval"):
                state.approve_candidate("conversation-1", "c-one", "v-two", root)
            result = state.approve_candidate("conversation-1", "c-one", "v-one", root)
            self.assertEqual(result["status"], "approved")

    def test_conversation_key_is_not_allowed_to_escape_state_root(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "unsafe_conversation_key"):
                state.activate_candidate("..\\escape", "c-one", "v-one", directory)


if __name__ == "__main__":
    unittest.main()
