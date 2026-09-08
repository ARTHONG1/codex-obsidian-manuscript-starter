import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import traceback
import unittest
import urllib.error
import urllib.parse
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


class RemoteDeletionTests(unittest.TestCase):
    """Exercise real REST listing/read/delete verification over an in-memory transport."""

    def setUp(self):
        self.state_root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(mock.patch.dict(os.environ, {"CODEX_OBSIDIAN_STATE_ROOT": str(self.state_root)}))
        self.bundle = "conversations/conv-1"
        self.metadata_path = f"{self.bundle}/metadata.json"
        self.files = {
            self.metadata_path: json.dumps({
                "conversation_key": "conv-1", "title": "Test", "turn_ids": [],
                "last_turn_id": None, "asset_hashes": {},
                "file_manifest": ["metadata.json", "conversation.md", "assets/image.png"],
            }).encode(),
            f"{self.bundle}/conversation.md": b"conversation",
            f"{self.bundle}/assets/image.png": b"image",
            "conversations/conv-10/conversation.md": b"unrelated",
        }
        self.deleted = []
        self.after_delete = lambda path: None
        self.fail_path = None
        self.keep_path = None
        self.retain_empty_directories = False
        rest = sys.modules[delete_bundle.read_vault_file.__module__]
        self.enterContext(mock.patch.object(rest, "_connection", return_value=("test", "https://127.0.0.1:1234", None)))
        self.enterContext(mock.patch.object(rest, "_request", side_effect=self.request))

    def request(self, url, token, method, **kwargs):
        path = urllib.parse.unquote(urllib.parse.urlsplit(url).path[len("/vault/"):])
        if method == "GET" and path.endswith("/"):
            children = set()
            for name in self.files:
                if name.startswith(path):
                    tail = name[len(path):]
                    children.add(tail.split("/", 1)[0] + ("/" if "/" in tail else ""))
            if children or (self.retain_empty_directories and path in {
                "conversations/conv-1/", "conversations/conv-1/assets/",
            }):
                return json.dumps({"files": sorted(children)}).encode()
        elif method == "GET" and path in self.files:
            return self.files[path]
        elif method == "DELETE":
            if path == self.fail_path:
                raise OSError("injected remote failure")
            self.deleted.append(path)
            if path != self.keep_path:
                self.files.pop(path, None)
            self.after_delete(path)
            return b""
        raise urllib.error.HTTPError(url, 404, "Not found", {}, None)

    def delete(self, **kwargs):
        return delete_bundle.delete_conversation_bundle(
            Path("unused-config.json"), "conversations", "conv-1", **kwargs
        )

    def test_success_deletes_metadata_last_and_preserves_exact_sibling(self):
        result = self.delete()
        self.assertEqual(result["status"], "deleted")
        self.assertEqual(result["deleted_files"], [
            "conversations/conv-1/assets/image.png",
            "conversations/conv-1/conversation.md",
            "conversations/conv-1/metadata.json",
        ])
        self.assertEqual(self.deleted[-1], self.metadata_path)
        self.assertEqual(self.files, {"conversations/conv-10/conversation.md": b"unrelated"})

    def test_success_is_idempotent(self):
        self.delete()
        result = self.delete()
        self.assertEqual(result["status"], "already_absent")
        self.assertEqual(result["deleted_files"], [])
        self.assertEqual(len(self.deleted), 3)

    def test_idempotence_when_rest_retains_empty_directories(self):
        self.retain_empty_directories = True
        self.delete()
        result = self.delete()
        self.assertEqual(result["status"], "already_absent")
        self.assertEqual(result["deleted_files"], [])

    def test_retry_after_failure_without_progress_succeeds(self):
        self.files.pop(f"{self.bundle}/assets/image.png")
        metadata = json.loads(self.files[self.metadata_path])
        metadata["file_manifest"] = ["metadata.json", "conversation.md"]
        self.files[self.metadata_path] = json.dumps(metadata).encode()
        self.fail_path = f"{self.bundle}/conversation.md"
        with self.assertRaisesRegex(RuntimeError, "metadata preserved; resume available"):
            self.delete()
        self.fail_path = None
        self.assertEqual(self.delete()["status"], "deleted")
        self.assertEqual(self.files, {"conversations/conv-10/conversation.md": b"unrelated"})

    def test_arbitrary_missing_manifest_file_rejected_before_deletion(self):
        self.files.pop(f"{self.bundle}/assets/image.png")
        before = dict(self.files)
        with self.assertRaisesRegex(RuntimeError, "file manifest mismatch"):
            self.delete()
        self.assertEqual(self.files, before)
        self.assertEqual(self.deleted, [])

    def test_metadata_delete_failure_preserves_metadata_and_resumes(self):
        self.fail_path = self.metadata_path
        with self.assertRaisesRegex(RuntimeError, "metadata preserved; resume available"):
            self.delete()
        self.assertIn(self.metadata_path, self.files)
        self.fail_path = None
        self.assertEqual(self.delete()["status"], "deleted")

    def test_sibling_change_blocks_final_metadata_delete(self):
        self.after_delete = lambda path: self.files.update({
            "conversations/conv-10/conversation.md": b"changed",
        })
        with self.assertRaisesRegex(RuntimeError, "unrelated conversation changed"):
            self.delete()
        self.assertIn(self.metadata_path, self.files)
        self.assertNotIn(self.metadata_path, self.deleted)

    def test_partial_delete_preserves_resume_journal(self):
        self.fail_path = f"{self.bundle}/conversation.md"
        with self.assertRaisesRegex(RuntimeError, "resume available"):
            self.delete()
        self.assertNotIn(f"{self.bundle}/assets/image.png", self.files)
        self.assertIn(self.metadata_path, self.files)
        journal = json.loads(next(self.state_root.rglob("*.json")).read_text())
        self.assertEqual(journal["verified"], ["assets/image.png"])
        self.assertEqual(journal["intent"], ["assets/image.png", "conversation.md"])

    def test_partial_retry_accepts_only_journaled_missing_files(self):
        self.fail_path = f"{self.bundle}/conversation.md"
        with self.assertRaises(RuntimeError):
            self.delete()
        self.fail_path = None
        self.assertEqual(self.delete()["status"], "deleted")
        self.assertEqual(list(self.state_root.rglob("*.json")), [])

    def test_crash_after_remote_delete_has_durable_intent_and_resumes(self):
        def crash(path):
            raise KeyboardInterrupt("crash after DELETE before verification")
        self.after_delete = crash
        with self.assertRaises(KeyboardInterrupt):
            self.delete()
        journal_path = next(self.state_root.rglob("*.json"))
        journal = json.loads(journal_path.read_text())
        self.assertEqual(journal["intent"], ["assets/image.png"])
        self.assertEqual(journal["verified"], [])
        self.after_delete = lambda path: None
        self.assertEqual(self.delete()["status"], "deleted")
        self.assertFalse(journal_path.exists())

    def test_crash_after_metadata_delete_resumes_cleanup(self):
        def crash(path):
            if path == self.metadata_path:
                raise KeyboardInterrupt("metadata DELETE completed")
        self.after_delete = crash
        with self.assertRaises(KeyboardInterrupt):
            self.delete()
        self.assertTrue(list(self.state_root.rglob("*.json")))
        self.after_delete = lambda path: None
        self.assertEqual(self.delete()["status"], "deleted")
        self.assertEqual(list(self.state_root.rglob("*.json")), [])

    def test_missing_unintended_file_after_crash_blocks_resume(self):
        self.after_delete = lambda path: (_ for _ in ()).throw(KeyboardInterrupt())
        with self.assertRaises(KeyboardInterrupt):
            self.delete()
        self.files.pop(f"{self.bundle}/conversation.md")
        self.after_delete = lambda path: None
        before = dict(self.files)
        with self.assertRaisesRegex(RuntimeError, "file manifest mismatch"):
            self.delete()
        self.assertEqual(self.files, before)

    def test_resume_blocks_new_files_changed_metadata_and_reappeared_files(self):
        self.fail_path = f"{self.bundle}/conversation.md"
        with self.assertRaises(RuntimeError):
            self.delete()
        self.fail_path = None
        clean = dict(self.files)
        for path, value in [
            (f"{self.bundle}/new.txt", b"new"),
            (self.metadata_path, self.files[self.metadata_path] + b" "),
            (f"{self.bundle}/assets/image.png", b"replacement"),
        ]:
            with self.subTest(path=path):
                self.files = {**clean, path: value}
                before = dict(self.files)
                with self.assertRaises(RuntimeError):
                    self.delete()
                self.assertEqual(self.files, before)
                self.assertTrue(list(self.state_root.rglob("*.json")))

    def test_journal_is_bound_to_config_identity_without_absolute_paths(self):
        self.fail_path = f"{self.bundle}/conversation.md"
        with self.assertRaises(RuntimeError):
            self.delete()
        journal_path = next(self.state_root.rglob("*.json"))
        text = journal_path.read_text()
        self.assertNotIn(str(Path("unused-config.json").resolve()), text)
        self.assertNotIn("unused-config.json", text)
        self.assertRegex(journal_path.stem, r"^[0-9a-f]{64}$")
        self.fail_path = None
        with self.assertRaisesRegex(RuntimeError, "file manifest mismatch"):
            delete_bundle.delete_conversation_bundle(Path("other-config.json"), "conversations", "conv-1")
        self.assertTrue(journal_path.exists())

    def test_override_server_cannot_resume_another_servers_journal(self):
        first = "https://127.0.0.1:1234"
        second = "https://127.0.0.1:5678"
        self.fail_path = f"{self.bundle}/conversation.md"
        with self.assertRaises(RuntimeError):
            self.delete(base_url=first)
        journal_path = next(self.state_root.rglob("*.json"))
        original = journal_path.read_bytes()
        self.assertNotIn(first.encode(), original)
        self.fail_path = None
        before = dict(self.files)
        with self.assertRaisesRegex(RuntimeError, "file manifest mismatch"):
            self.delete(base_url=second)
        self.assertEqual(self.files, before)
        self.assertEqual(journal_path.read_bytes(), original)
        self.assertEqual(self.delete(base_url=first)["status"], "deleted")
        self.assertFalse(journal_path.exists())

    def test_endpoint_aliases_share_resume_journal(self):
        for configured in (False, True):
            with self.subTest(configured=configured):
                config = self.state_root / "alias-config.txt"
                if configured:
                    config.write_text(json.dumps({"port": 1234, "apiKey": "test"}))
                self.fail_path = f"{self.bundle}/conversation.md"
                first = None if configured else "https://127.0.0.1:1234"
                with self.assertRaises(RuntimeError):
                    delete_bundle.delete_conversation_bundle(config, "conversations", "conv-1", first)
                before = list(self.state_root.rglob("*.json"))
                self.assertEqual(len(before), 1)
                self.fail_path = None
                result = delete_bundle.delete_conversation_bundle(config, "conversations", "conv-1", "https://127.0.0.1:1234/")
                self.assertEqual(result["status"], "deleted")
                self.assertEqual(list(self.state_root.rglob("*.json")), [])
                # Restore the remote fixture for the second independent case.
                self.files[self.metadata_path] = json.dumps({
                    "conversation_key": "conv-1", "file_manifest": ["metadata.json", "conversation.md", "assets/image.png"],
                }).encode()
                self.files[f"{self.bundle}/conversation.md"] = b"conversation"
                self.files[f"{self.bundle}/assets/image.png"] = b"image"

    def test_endpoint_aliases_share_bounded_lock(self):
        config = self.state_root / "alias-config.txt"
        config.write_text(json.dumps({"port": 1234, "apiKey": "test"}))
        with delete_bundle._journal_lock(config, self.bundle):
            for alias in ("https://127.0.0.1:1234", "https://127.0.0.1:1234/"):
                with self.subTest(alias=alias), self.assertRaisesRegex(RuntimeError, "deletion_busy"):
                    with delete_bundle._journal_lock(config, self.bundle, alias):
                        self.fail("alias acquired a second lock")

    def test_partial_failure_does_not_disclose_transport_exception_or_chain(self):
        for exception_type in (OSError, RuntimeError):
            with self.subTest(exception_type=exception_type):
                def fail(path):
                    raise exception_type("Authorization: Bearer FAKE-TEST-CREDENTIAL")
                self.after_delete = fail
                try:
                    self.delete()
                except RuntimeError as error:
                    rendered = "".join(traceback.format_exception(error))
                    self.assertNotIn("FAKE-TEST-CREDENTIAL", rendered)
                    self.assertIn(exception_type.__name__, str(error))
                    self.assertIn("partial_delete_failed", str(error))
                else:
                    self.fail("expected partial failure")
                self.assertTrue(list(self.state_root.rglob("*.json")))

    def test_concurrent_same_bundle_is_bounded_and_cannot_delete(self):
        def compete(path):
            before = dict(self.files)
            with self.assertRaisesRegex(RuntimeError, "deletion_busy"):
                self.delete()
            self.assertEqual(self.files, before)
        self.after_delete = compete
        self.assertEqual(self.delete()["status"], "deleted")

    def test_state_reparse_point_is_rejected_before_remote_deletion(self):
        original_lstat = os.lstat
        def reparse(path, *args, **kwargs):
            value = original_lstat(path, *args, **kwargs)
            if Path(path) == self.state_root:
                return type("ReparseStat", (), {"st_mode": value.st_mode,
                    "st_file_attributes": stat.FILE_ATTRIBUTE_REPARSE_POINT})()
            return value
        with mock.patch.object(os, "lstat", side_effect=reparse):
            with self.assertRaisesRegex(ValueError, "reparse|symlink"):
                self.delete()
        self.assertEqual(self.deleted, [])

    def test_journal_write_failure_prevents_unjournaled_remote_delete(self):
        original_replace = os.replace
        writes = 0
        def fail_intent(source, target):
            nonlocal writes
            writes += 1
            if writes == 2:
                raise OSError("disk full before durable intent")
            return original_replace(source, target)
        with mock.patch.object(os, "replace", side_effect=fail_intent):
            with self.assertRaisesRegex(RuntimeError, "OSError"):
                self.delete()
        self.assertEqual(self.deleted, [])
        self.assertEqual(json.loads(next(self.state_root.rglob("*.json")).read_text())["intent"], [])
        self.assertEqual(self.delete()["status"], "deleted")

    def test_transient_permission_at_intent_replace_retries_before_remote_delete(self):
        original_replace = os.replace
        calls = 0
        def transient(source, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.assertEqual(self.deleted, [])
                raise PermissionError(13, "injected transient sharing conflict")
            if calls == 3:
                self.assertEqual(self.deleted, [])
            return original_replace(source, target)
        with mock.patch.object(os, "replace", side_effect=transient):
            self.assertEqual(self.delete()["status"], "deleted")
        self.assertEqual(len(self.deleted), 3)
        self.assertEqual(self.deleted[-1], self.metadata_path)
        self.assertEqual(list(self.state_root.rglob("*.json")), [])

    def test_permission_replace_retry_exhaustion_preserves_durable_journal(self):
        original_replace = os.replace
        calls = 0
        def persistent(source, target):
            nonlocal calls
            calls += 1
            if calls > 1:
                raise PermissionError(13, "injected persistent sharing conflict")
            return original_replace(source, target)
        with mock.patch.object(os, "replace", side_effect=persistent):
            with self.assertRaisesRegex(RuntimeError, "partial_delete_failed.*PermissionError"):
                self.delete()
        self.assertEqual(calls, 6)  # Initial snapshot plus five bounded intent attempts.
        self.assertEqual(self.deleted, [])
        journal = json.loads(next(self.state_root.rglob("*.json")).read_text())
        self.assertEqual(journal["intent"], [])
        self.assertEqual(journal["verified"], [])
        self.assertEqual(list(self.state_root.rglob("*.tmp")), [])
        self.assertEqual(self.delete()["status"], "deleted")

    def test_verified_progress_write_failure_resumes_from_durable_intent(self):
        original_replace = os.replace
        writes = 0
        def fail_progress(source, target):
            nonlocal writes
            writes += 1
            if writes == 3:
                raise OSError("disk full after remote delete")
            return original_replace(source, target)
        with mock.patch.object(os, "replace", side_effect=fail_progress):
            with self.assertRaisesRegex(RuntimeError, "OSError"):
                self.delete()
        journal = json.loads(next(self.state_root.rglob("*.json")).read_text())
        self.assertEqual(journal["intent"], ["assets/image.png"])
        self.assertEqual(journal["verified"], [])
        self.assertEqual(self.delete()["status"], "deleted")

    def test_corrupted_journal_is_preserved_and_blocks_remote_delete(self):
        self.fail_path = f"{self.bundle}/conversation.md"
        with self.assertRaises(RuntimeError):
            self.delete()
        journal_path = next(self.state_root.rglob("*.json"))
        original = json.loads(journal_path.read_text())
        for changes in [
            {"key": "0" * 64}, {"files": ["metadata.json"]},
            {"intent": ["../conv-10/conversation.md"]},
            {"verified": ["metadata.json"]}, {"metadata_hash": "invalid"},
        ]:
            with self.subTest(changes=changes):
                journal_path.write_text(json.dumps({**original, **changes}))
                before = dict(self.files)
                with self.assertRaises((RuntimeError, ValueError)):
                    self.delete()
                self.assertEqual(self.files, before)
                self.assertTrue(journal_path.exists())

    def test_config_contents_are_hashed_not_stored_and_changes_block_resume(self):
        config = self.state_root / "config.txt"
        config.write_text('{"apiKey":"NEVER-PERSIST-THIS-SECRET"}')
        self.fail_path = f"{self.bundle}/conversation.md"
        with self.assertRaises(RuntimeError):
            delete_bundle.delete_conversation_bundle(config, "conversations", "conv-1")
        journal_path = next(self.state_root.rglob("*.json"))
        self.assertNotIn("NEVER-PERSIST-THIS-SECRET", journal_path.read_text())
        self.assertNotIn(str(config), journal_path.read_text())
        config.write_text('{"apiKey":"changed"}')
        before = dict(self.files)
        with self.assertRaisesRegex(RuntimeError, "journal identity"):
            delete_bundle.delete_conversation_bundle(config, "conversations", "conv-1")
        self.assertEqual(self.files, before)

    def test_completion_does_not_remove_another_bundles_journal(self):
        directory = self.state_root / "deletion-journals"
        directory.mkdir()
        unrelated = directory / ("f" * 64 + ".json")
        unrelated.write_text("unrelated state")
        self.delete()
        self.assertEqual(unrelated.read_text(), "unrelated state")
        self.assertEqual(list(directory.glob("*.json")), [unrelated])

    def test_process_exit_releases_lock_without_stale_lock_deletion(self):
        code = (
            "import importlib.util, os; from pathlib import Path; "
            "s=importlib.util.spec_from_file_location('delete_bundle', " + repr(str(SCRIPT)) + "); "
            "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
            "lock=m._journal_lock(Path('unused-config.json'), 'conversations/conv-1'); "
            "lock.__enter__(); os._exit(17)"
        )
        child = subprocess.run([sys.executable, "-c", code], capture_output=True, timeout=10)
        self.assertEqual(child.returncode, 17, child.stderr)
        self.assertTrue(list(self.state_root.rglob("*.lock")))
        self.assertEqual(self.delete()["status"], "deleted")

    def test_remote_directory_cannot_escape_exact_bundle_scope(self):
        with mock.patch.object(delete_bundle, "list_vault_directory", return_value=["../conv-10/conversation.md"]):
            with self.assertRaisesRegex(ValueError, "directory child"):
                self.delete()
        self.assertEqual(self.deleted, [])

    def test_unexpected_file_rejected_before_deletion(self):
        self.files[f"{self.bundle}/untracked.txt"] = b"keep"
        before = dict(self.files)
        with self.assertRaisesRegex(RuntimeError, "file manifest mismatch"):
            self.delete()
        self.assertEqual(self.files, before)
        self.assertEqual(self.deleted, [])

    def test_concurrent_metadata_change_preserves_new_metadata(self):
        def change(path):
            if path.endswith("conversation.md"):
                self.files[self.metadata_path] = b'{"conversation_key":"new"}'
        self.after_delete = change
        with self.assertRaisesRegex(RuntimeError, "metadata changed after snapshot"):
            self.delete()
        self.assertEqual(self.files[self.metadata_path], b'{"conversation_key":"new"}')
        self.assertNotIn(self.metadata_path, self.deleted)

    def test_concurrent_unexpected_file_blocks_metadata_deletion(self):
        self.after_delete = lambda path: self.files.update({f"{self.bundle}/new.txt": b"keep"})
        with self.assertRaisesRegex(RuntimeError, "still present: .*new.txt"):
            self.delete()
        self.assertIn(self.metadata_path, self.files)
        self.assertEqual(self.files[f"{self.bundle}/new.txt"], b"keep")

    def test_remote_verification_failure_never_falls_back_to_filesystem(self):
        self.keep_path = f"{self.bundle}/conversation.md"
        with mock.patch.object(delete_bundle, "remove_empty_bundle_directories") as cleanup:
            with self.assertRaisesRegex(RuntimeError, "partial_delete_failed"):
                self.delete(vault_root=Path("must-not-touch"))
        cleanup.assert_not_called()
        self.assertIn(self.keep_path, self.files)
        self.assertIn(self.metadata_path, self.files)

    def test_file_arriving_during_metadata_delete_prevents_success(self):
        def change(path):
            if path == self.metadata_path:
                self.files[f"{self.bundle}/new.txt"] = b"keep"
        self.after_delete = change
        with self.assertRaisesRegex(RuntimeError, "resume blocked.*still present: .*new.txt"):
            self.delete()
        self.assertEqual(self.files[f"{self.bundle}/new.txt"], b"keep")


class DeleteConversationBundleTests(unittest.TestCase):
    def setUp(self):
        state = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(mock.patch.dict(os.environ, {"CODEX_OBSIDIAN_STATE_ROOT": state}))

    def _directory_link(self, link, target):
        if os.name == "nt":
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(target)],
                capture_output=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            link.symlink_to(target, target_is_directory=True)

    def test_physical_bundle_junction_cannot_remove_empty_sibling(self):
        vault = Path(self.enterContext(tempfile.TemporaryDirectory()))
        sibling = vault / "conversations" / "conv-2"
        sibling.mkdir(parents=True)
        target = vault / "conversations" / "conv-1"
        self._directory_link(target, sibling)
        with self.assertRaisesRegex(ValueError, "symlink|reparse"):
            delete_bundle.remove_empty_bundle_directories(vault, "conversations", "conv-1")
        self.assertTrue(sibling.is_dir())
        self.assertTrue(target.exists())

    def test_physical_nested_junction_blocks_all_directory_removal(self):
        vault = Path(self.enterContext(tempfile.TemporaryDirectory()))
        target = vault / "conversations" / "conv-1"
        (target / "empty").mkdir(parents=True)
        sibling = vault / "conversations" / "conv-2"
        sibling.mkdir()
        self._directory_link(target / "assets", sibling)
        with self.assertRaisesRegex(ValueError, "symlink|reparse"):
            delete_bundle.remove_empty_bundle_directories(vault, "conversations", "conv-1")
        self.assertTrue((target / "empty").is_dir())
        self.assertTrue((target / "assets").exists())
        self.assertTrue(sibling.is_dir())

    def test_physical_regular_empty_bundle_is_removed_without_touching_sibling(self):
        vault = Path(self.enterContext(tempfile.TemporaryDirectory()))
        target = vault / "conversations" / "conv-1"
        (target / "assets" / "nested").mkdir(parents=True)
        sibling = vault / "conversations" / "conv-2"
        sibling.mkdir()
        self.assertTrue(delete_bundle.remove_empty_bundle_directories(vault, "conversations", "conv-1"))
        self.assertFalse(target.exists())
        self.assertTrue(sibling.is_dir())

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

        class InjectedSiblingFailure(OSError):
            pass

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
                raise InjectedSiblingFailure("injected sibling failure")
            payloads.pop(path, None)
            return path

        with mock.patch.multiple(
            delete_bundle,
            list_vault_directory=list_directory,
            read_vault_file=read_file,
            delete_and_verify=delete_file,
        ):
            with self.assertRaisesRegex(RuntimeError, "metadata preserved; resume available.*InjectedSiblingFailure"):
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
