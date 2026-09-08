import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from types import SimpleNamespace
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
    def test_registration_lock_rejects_state_junction_before_creating_children(self):
        for nested in (False, True):
            with self.subTest(nested=nested), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                target = root / "target"
                target.mkdir()
                link = root / "state"
                if os.name == "nt":
                    import _winapi
                    _winapi.CreateJunction(str(target), str(link))
                else:
                    link.symlink_to(target, target_is_directory=True)
                try:
                    state_root = link / "nested" if nested else link
                    with patch.dict("os.environ", {"CODEX_OBSIDIAN_STATE_ROOT": str(state_root)}):
                        with self.assertRaisesRegex(ValueError, "unsafe_template_lock_path"):
                            with registration._registration_lock("c-one"):
                                pass
                    self.assertEqual(list(target.iterdir()), [])
                finally:
                    link.rmdir() if os.name == "nt" else link.unlink()

    def test_registration_lock_rejects_reparse_lock_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            locks = root / "locks"
            locks.mkdir()
            target = root / "target"
            target.mkdir()
            link = locks / "template-c-one.lock"
            if os.name == "nt":
                import _winapi
                _winapi.CreateJunction(str(target), str(link))
            else:
                link.symlink_to(target, target_is_directory=True)
            try:
                with patch.dict("os.environ", {"CODEX_OBSIDIAN_STATE_ROOT": str(root)}):
                    with self.assertRaisesRegex(ValueError, "unsafe_template_lock_path"):
                        with registration._registration_lock("c-one"):
                            pass
            finally:
                link.rmdir() if os.name == "nt" else link.unlink()

    def test_registration_lock_rechecks_reparse_metadata_before_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock = root / "locks" / "template-c-one.lock"
            original_lstat = Path.lstat
            cleanup = False

            def changed_metadata(path, *args, **kwargs):
                info = original_lstat(path, *args, **kwargs)
                if cleanup and path == lock:
                    return SimpleNamespace(st_mode=info.st_mode,
                                           st_file_attributes=0x400)
                return info

            # Simulate the OS reporting a replacement reparse point after yield;
            # Windows does not allow replacing this open file in-process.
            with patch.dict("os.environ", {"CODEX_OBSIDIAN_STATE_ROOT": str(root)}):
                with self.assertRaisesRegex(ValueError, "unsafe_template_lock_path"):
                    with patch.object(Path, "lstat", changed_metadata):
                        with registration._registration_lock("c-one"):
                            cleanup = True
            self.assertTrue(lock.is_file(), "Unsafe cleanup must not unlink the replacement path")

    def candidate(self, root: Path, status="preview_ready") -> Path:
        candidate = root / "candidate"
        candidate.mkdir()
        template = {"schema_version": 1, "template_profile": "custom_manuscript_template",
                    "display_name": "A", "status": "candidate", "blocks": [{"component": "paragraphs"}]}
        analysis = {"status": "safe_for_preview", "source_manifest": [], "evidence": []}
        preview = {"marker": "preview"}
        canonical = json.dumps({"schema_version": 1, "analysis": analysis, "template": template, "preview": preview},
                               ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        candidate_id = "c-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
        for name, content in {
            "template.json": template | {"candidate_id": candidate_id},
            "source-manifest.json": {"sources": [], "evidence": []},
            "source-analysis.json": analysis,
            "preview-content.json": preview,
        }.items():
            (candidate / name).write_text(json.dumps(content), encoding="utf-8")
        return candidate

    def approval(self, candidate, state_root):
        candidate_id = json.loads((candidate / "template.json").read_text(encoding="utf-8"))["candidate_id"]
        hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in candidate.iterdir()}
        canonical = json.dumps(hashes, sort_keys=True, separators=(",", ":"))
        validation_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        activate_candidate("conversation-1", candidate_id, validation_hash, state_root)
        approve_candidate("conversation-1", candidate_id, validation_hash, state_root)
        return {"candidate_id": candidate_id, "approved_candidate_id": candidate_id,
                "conversation_key": "conversation-1",  # gitleaks:allow
                "validation_hash": validation_hash, "status": "preview_ready"}

    def test_requires_exact_candidate_and_preview_ready(self):
        with self.assertRaisesRegex(ValueError, "template_preview_not_ready"):
            registration.register_candidate({}, Path("candidate"), {"candidate_id": "c-one", "approved_candidate_id": "c-one", "status": "needs_review"}, transport=FakeRest())

    def test_extra_directories_are_not_ignored_by_candidate_allowlist(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate = self.candidate(Path(directory))
            (candidate / "preview").mkdir()
            with self.assertRaisesRegex(ValueError, "allowlist"):
                registration.candidate_validation_hash(candidate)

    def test_candidate_and_ancestor_junctions_are_rejected(self):
        for ancestor in (False, True):
            with self.subTest(ancestor=ancestor), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                real = root / "real"
                real.mkdir()
                candidate = self.candidate(real)
                link = root / "linked"
                target = real if ancestor else candidate
                if os.name == "nt":
                    import _winapi
                    _winapi.CreateJunction(str(target), str(link))
                else:
                    link.symlink_to(target, target_is_directory=True)
                try:
                    selected = link / "candidate" if ancestor else link
                    with self.assertRaisesRegex(ValueError, "unsafe_template_candidate_path"):
                        registration.candidate_validation_hash(selected)
                finally:
                    # Only remove this synthetic link, never its target tree.
                    if os.name == "nt":
                        link.rmdir()
                    else:
                        link.unlink()

    def test_parent_traversal_cannot_hide_a_reparse_ancestor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = self.candidate(root)
            (root / "child").mkdir()
            with self.assertRaisesRegex(ValueError, "unsafe_template_candidate_path"):
                registration.candidate_validation_hash(root / "child" / ".." / candidate.name)

    def test_oversized_json_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate = self.candidate(Path(directory))
            path = candidate / "source-analysis.json"
            content = path.read_bytes()
            path.write_bytes(content + b" " * (4 * 1024 * 1024 + 1 - len(content)))
            with self.assertRaisesRegex(ValueError, "too_large"):
                registration.candidate_validation_hash(candidate)

    def test_total_json_snapshot_size_is_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate = self.candidate(Path(directory))
            for name in ("source-analysis.json", "source-manifest.json", "preview-content.json"):
                path = candidate / name
                content = path.read_bytes()
                path.write_bytes(content + b" " * (3 * 1024 * 1024 - len(content)))
            with self.assertRaisesRegex(ValueError, "too_large"):
                registration.candidate_validation_hash(candidate)

    def test_snapshot_exactly_at_byte_limits_remains_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate = self.candidate(Path(directory))
            first = candidate / "source-analysis.json"
            content = first.read_bytes()
            first.write_bytes(content + b" " * (4 * 1024 * 1024 - len(content)))
            second = candidate / "preview-content.json"
            current_total = sum(path.stat().st_size for path in candidate.iterdir())
            second.write_bytes(second.read_bytes() + b" " * (8 * 1024 * 1024 - current_total))
            self.assertEqual(len(registration.candidate_validation_hash(candidate)), 64)

    def test_allocates_immutable_template_version_and_reads_back_every_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = self.candidate(root)
            fake = FakeRest()
            with patch.dict("os.environ", {"CODEX_OBSIDIAN_STATE_ROOT": str(root / "state")}):
                approval = self.approval(candidate, root / "state")
                result = registration.register_candidate({}, candidate, approval, transport=fake)
            self.assertEqual(result["version"], "t0.1")
            remote = f'_system/manuscript-template-registry/{approval["candidate_id"]}/t0.1'
            self.assertTrue(all(path.startswith(remote + "/") for path in fake.writes))
            self.assertIn(remote + "/registry.json", fake.files)

    def test_each_payload_change_after_approval_is_rejected_before_rest_writes(self):
        for filename in ("template.json", "source-manifest.json", "source-analysis.json", "preview-content.json"):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                candidate = self.candidate(root)
                fake = FakeRest()
                with patch.dict("os.environ", {"CODEX_OBSIDIAN_STATE_ROOT": str(root / "state")}):
                    approval = self.approval(candidate, root / "state")
                    # Even a byte-only change invalidates the approved snapshot.
                    path = candidate / filename
                    path.write_bytes(path.read_bytes() + b" ")
                    with self.assertRaisesRegex(ValueError, "stale_candidate_approval"):
                        registration.register_candidate({}, candidate, approval, transport=fake)
                self.assertEqual(fake.writes, [])

    def test_canonical_candidate_id_is_checked_even_with_fresh_payload_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = self.candidate(root)
            path = candidate / "template.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["blocks"] = [{"component": "title"}]
            path.write_text(json.dumps(value), encoding="utf-8")
            fake = FakeRest()
            with patch.dict("os.environ", {"CODEX_OBSIDIAN_STATE_ROOT": str(root / "state")}):
                approval = self.approval(candidate, root / "state")
                with self.assertRaisesRegex(ValueError, "stale_candidate_approval"):
                    registration.register_candidate({}, candidate, approval, transport=fake)
            self.assertEqual(fake.writes, [])

    def test_trailing_slash_versions_are_not_overwritten(self):
        class DirectoryRest(FakeRest):
            def list(self, config, directory, base_url=None):
                return [name + "/" for name in super().list(config, directory, base_url) or []]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = self.candidate(root)
            fake = DirectoryRest()
            with patch.dict("os.environ", {"CODEX_OBSIDIAN_STATE_ROOT": str(root / "state")}):
                approval = self.approval(candidate, root / "state")
                first = registration.register_candidate({}, candidate, approval, transport=fake)
                existing = dict(fake.files)
                second = registration.register_candidate({}, candidate, approval, transport=fake)
            self.assertEqual(first["version"], "t0.1")
            self.assertEqual(second["version"], "t0.2")
            self.assertTrue(all(fake.files[path] == content for path, content in existing.items()))

    def test_candidate_validation_hash_can_be_used_for_real_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = self.candidate(root)
            approval = self.approval(candidate, root / "state")
            hasher = getattr(registration, "candidate_validation_hash", None)
            self.assertTrue(callable(hasher), "Approval must bind to a reproducible full snapshot hash")
            self.assertEqual(hasher(candidate), approval["validation_hash"])

    def test_registered_snapshot_resolves_to_the_exact_approved_template(self):
        from resolve_custom_template import resolve_template

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = self.candidate(root)
            fake = FakeRest()
            with patch.dict("os.environ", {"CODEX_OBSIDIAN_STATE_ROOT": str(root / "state")}):
                approval = self.approval(candidate, root / "state")
                registered = registration.register_candidate({}, candidate, approval, transport=fake)
                result = resolve_template({}, "A", transport=fake)
            self.assertEqual(result["template"], json.loads((candidate / "template.json").read_text(encoding="utf-8")))
            self.assertEqual(result["status"], "approved")
            self.assertEqual(result["remote_root"], registered["remote_root"])
            self.assertIs(result["snapshot_verified"], True)
            approved_hash = hashlib.sha256(json.dumps(result["files"], sort_keys=True,
                                                      separators=(",", ":")).encode("utf-8")).hexdigest()
            self.assertEqual(approved_hash, approval["validation_hash"])

    def test_fresh_approval_does_not_bypass_source_or_template_validation(self):
        for filename, change in (
            ("source-manifest.json", {"sources": [{"name": "different"}]}),
            ("source-analysis.json", {"status": "unsafe_source"}),
            ("source-analysis.json", {"critical_unresolved": ["missing layout"]}),
            ("template.json", {"blocks": [{"component": "script"}]}),
        ):
            with self.subTest(filename=filename, change=change), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                candidate = self.candidate(root)
                path = candidate / filename
                value = json.loads(path.read_text(encoding="utf-8")) | change
                path.write_text(json.dumps(value), encoding="utf-8")
                fake = FakeRest()
                with patch.dict("os.environ", {"CODEX_OBSIDIAN_STATE_ROOT": str(root / "state")}):
                    approval = self.approval(candidate, root / "state")
                    with self.assertRaises(ValueError):
                        registration.register_candidate({}, candidate, approval, transport=fake)
                self.assertEqual(fake.writes, [])

    def test_local_registry_root_is_not_accepted_as_a_vault_write_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "registration_requires_local_rest"):
                registration.register_candidate({}, Path(directory), {"candidate_id": "c-one", "approved_candidate_id": "c-one", "status": "preview_ready"})


if __name__ == "__main__":
    unittest.main()
