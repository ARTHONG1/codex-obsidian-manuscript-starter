import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    REPOSITORY_ROOT
    / "plugins"
    / "obsidian-manuscript-publisher"
    / "skills"
    / "obsidian-manuscript-publisher"
    / "scripts"
    / "delete_conversation_bundle.py"
)


spec = importlib.util.spec_from_file_location("delete_conversation_bundle", SCRIPT)
delete_bundle = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = delete_bundle
spec.loader.exec_module(delete_bundle)


class DeleteConversationBundleTests(unittest.TestCase):
    def _fixture(self):
        temp_dir = tempfile.TemporaryDirectory()
        vault_root = Path(temp_dir.name)
        bundle = vault_root / "conversations" / "conv-1"
        bundle.mkdir(parents=True)
        files = {
            "conversations/conv-1/metadata.json": {
                "conversation_key": "conv-1",
                "file_manifest": ["metadata.json", "conversation.md"],
            },
            "conversations/conv-1/conversation.md": b"conversation",
        }
        payloads = {}
        for relative_path, content in files.items():
            path = vault_root / Path(*relative_path.split("/"))
            if isinstance(content, dict):
                content = json.dumps(content).encode("utf-8")
            path.write_bytes(content)
            payloads[relative_path] = content
        return temp_dir, vault_root, payloads

    def test_failure_while_deleting_sibling_preserves_metadata_for_resume(self):
        temp_dir, vault_root, payloads = self._fixture()
        self.addCleanup(temp_dir.cleanup)
        calls = []

        def list_directory(_config, directory, _base_url=None):
            if directory == "conversations/conv-1":
                return [
                    path.rsplit("/", 1)[1]
                    for path in payloads
                    if path.startswith("conversations/conv-1/")
                ]
            return []

        def read_file(_config, path, _base_url=None):
            return payloads.get(path)

        def delete_file(_config, path, _base_url=None):
            calls.append(path)
            if path.endswith("conversation.md"):
                raise OSError("injected sibling failure")
            payloads.pop(path, None)
            return path

        with mock.patch.multiple(
            delete_bundle,
            list_vault_directory=list_directory,
            read_vault_file=read_file,
            delete_and_verify=delete_file,
        ):
            with self.assertRaisesRegex(RuntimeError, "metadata preserved; resume available"):
                delete_bundle.delete_conversation_bundle(
                    Path("unused-config.json"), "conversations", "conv-1", vault_root=vault_root
                )

        self.assertIn("conversations/conv-1/conversation.md", calls)
        self.assertIn("conversations/conv-1/metadata.json", payloads)

    def test_metadata_change_after_snapshot_blocks_final_metadata_delete(self):
        temp_dir, vault_root, payloads = self._fixture()
        self.addCleanup(temp_dir.cleanup)

        def list_directory(_config, directory, _base_url=None):
            if directory == "conversations/conv-1":
                return [
                    path.rsplit("/", 1)[1]
                    for path in payloads
                    if path.startswith("conversations/conv-1/")
                ]
            return []

        def read_file(_config, path, _base_url=None):
            return payloads.get(path)

        def delete_file(_config, path, _base_url=None):
            payloads.pop(path, None)
            if path.endswith("conversation.md"):
                payloads["conversations/conv-1/metadata.json"] = b'{"conversation_key":"changed"}'
            return path

        with mock.patch.multiple(
            delete_bundle,
            list_vault_directory=list_directory,
            read_vault_file=read_file,
            delete_and_verify=delete_file,
        ):
            with self.assertRaisesRegex(RuntimeError, "metadata changed after snapshot"):
                delete_bundle.delete_conversation_bundle(
                    Path("unused-config.json"), "conversations", "conv-1", vault_root=vault_root
                )

        self.assertIn("conversations/conv-1/metadata.json", payloads)


if __name__ == "__main__":
    unittest.main()
