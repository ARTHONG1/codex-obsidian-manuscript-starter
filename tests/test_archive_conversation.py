import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    REPO_ROOT
    / "plugins"
    / "obsidian-manuscript-publisher"
    / "skills"
    / "obsidian-manuscript-publisher"
    / "scripts"
    / "archive_conversation.py"
)


class ArchiveConversationCliTests(unittest.TestCase):
    def test_cli_archives_json_turns_and_prints_result(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "00 Conversations"
            turns = Path(temp_dir) / "turns.json"
            turns.write_text(
                json.dumps([{"id": "turn-1", "role": "user", "text": "hello"}]),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--conversations-root",
                    str(root),
                    "--conversation-key",
                    "thread-1",
                    "--title",
                    "Test conversation",
                    "--turns-json",
                    str(turns),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["new_turn_count"], 1)
            self.assertTrue((root / "thread-1" / "conversation.md").is_file())
            self.assertEqual(
                (root / "thread-1" / "metadata.json").read_text(encoding="utf-8")
                .count("turn-1"),
                2,
            )


if __name__ == "__main__":
    unittest.main()
