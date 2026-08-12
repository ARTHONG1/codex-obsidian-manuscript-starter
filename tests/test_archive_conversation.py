import json
import importlib.util
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


def load_archive_module():
    spec = importlib.util.spec_from_file_location("archive_conversation", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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

    def test_publish_bundle_rejects_an_untrusted_link_before_any_vault_write(self):
        module = load_archive_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "00 Conversations"
            archived = module.archive_conversation(
                root,
                "thread-1",
                "Test conversation",
                [{"id": "turn-1", "role": "user", "text": "hello"}],
            )
            bundle = Path(archived["bundle_path"])
            external = bundle / "assets" / "external.txt"
            external.write_text("must not be uploaded", encoding="utf-8")
            original_reason = module._unsafe_link_reason

            def fake_reason(path):
                if Path(path).name == "external.txt":
                    return "symbolic link"
                return original_reason(path)

            from unittest import mock
            with (
                mock.patch.object(module, "_unsafe_link_reason", side_effect=fake_reason),
                mock.patch.object(module, "save_and_verify") as save,
            ):
                with self.assertRaisesRegex(ValueError, "symbolic link"):
                    module.publish_bundle(
                        Path("unused-config.json"),
                        bundle,
                        "01 Projects/Example/00 Conversations/thread-1",
                    )

            save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
