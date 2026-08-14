import importlib.util
import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).parents[1] / "plugins" / "obsidian-manuscript-publisher" / "skills" / "obsidian-manuscript-publisher" / "scripts"
SPEC = importlib.util.spec_from_file_location("template_source", SCRIPT_DIR / "template_source.py")
template_source = importlib.util.module_from_spec(SPEC)
try:
    sys.modules["template_source"] = template_source
    SPEC.loader.exec_module(template_source)
except FileNotFoundError:
    template_source = None


class TemplateSourceSecurityTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(template_source, "template_source.py must exist")

    def test_rejects_unsupported_and_macro_extensions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "example.docm").write_bytes(b"PK")
            (root / "example.doc").write_bytes(b"legacy")
            self.assertEqual(template_source.inspect_source(root / "example.docm").code, "unsupported_template_source")
            self.assertEqual(template_source.inspect_source(root / "example.doc").code, "unsupported_template_source")

    def test_rejects_source_above_per_file_limit_before_parsing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large.png"
            with path.open("wb") as stream:
                stream.truncate(template_source.MAX_SOURCE_BYTES + 1)
            result = template_source.inspect_source(path)
            self.assertEqual(result.code, "template_source_too_large")

    def test_canonical_manifest_does_not_expose_absolute_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example.png"
            path.write_bytes(b"not-a-real-image")
            result = template_source.inspect_source(path)
            self.assertEqual(result.code, "invalid_source_signature")
            self.assertNotIn(str(path), result.to_dict())

    def test_rejects_a_source_set_above_file_count_before_parsing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for index in range(template_source.MAX_SOURCE_FILES + 1):
                path = root / f"{index}.png"
                path.write_bytes(b"not-an-image")
                paths.append(path)
            result = template_source.inspect_source_set(paths)
            self.assertEqual(result["code"], "template_source_count_exceeded")
            self.assertNotIn(str(root), result)

    def test_source_set_manifest_is_deterministic_and_uses_aggregate_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "b.png"
            second = root / "a.png"
            first.write_bytes(b"\x89PNG\r\n\x1a\n" + b"b")
            second.write_bytes(b"\x89PNG\r\n\x1a\n" + b"a")
            result = template_source.inspect_source_set([first, second])
            self.assertEqual(result["code"], "source_set_ready")
            self.assertEqual([item["file_name"] for item in result["sources"]], ["a.png", "b.png"])

    def test_rejects_reparse_point_without_following_it_when_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.png"
            target.write_bytes(b"\x89PNG\r\n\x1a\n")
            link = root / "link.png"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink unavailable: {exc}")
            result = template_source.inspect_source(link)
            self.assertEqual(result.code, "unsafe_source_path")

    def test_snapshot_source_is_immutable_and_manifest_is_path_free(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "example.png"
            original = b"\x89PNG\r\n\x1a\noriginal"
            source.write_bytes(original)
            with template_source.snapshot_source_set([source], staging_parent=root) as snapshots:
                snapshot = snapshots[0]
                self.assertEqual(snapshot.safe_name, "example.png")
                self.assertEqual(snapshot.size_bytes, len(original))
                self.assertEqual(snapshot.sha256, hashlib.sha256(original).hexdigest())
                self.assertNotIn(str(snapshot.path), snapshot.to_manifest())
                self.assertTrue(snapshot.path.parent.name.startswith("codex-template-snapshot-"))
                source.write_bytes(b"\x89PNG\r\n\x1a\nmutated")
                self.assertEqual(snapshot.path.read_bytes(), original)

    def test_snapshot_detects_source_mutation_after_inspection(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "example.png"
            source.write_bytes(b"\x89PNG\r\n\x1a\noriginal")
            original_inspect = template_source.inspect_source

            def inspect_then_mutate(path):
                result = original_inspect(path)
                Path(path).write_bytes(b"\x89PNG\r\n\x1a\nchanged")
                return result

            template_source.inspect_source = inspect_then_mutate
            try:
                with self.assertRaisesRegex(
                    template_source.TemplateSourceError,
                    "source_changed_during_snapshot",
                ):
                    with template_source.snapshot_source_set([source]):
                        pass
            finally:
                template_source.inspect_source = original_inspect

    def test_snapshot_cleanup_removes_only_owned_directory_on_success_and_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "example.png"
            source.write_bytes(b"\x89PNG\r\n\x1a\ncontent")
            neighbor = root / "neighbor.txt"
            neighbor.write_text("keep", encoding="utf-8")
            captured = []
            with template_source.snapshot_source_set([source], staging_parent=root) as snapshots:
                captured.append(snapshots[0].path.parent)
            self.assertFalse(captured[0].exists())
            self.assertEqual(neighbor.read_text(encoding="utf-8"), "keep")
            with self.assertRaisesRegex(RuntimeError, "extractor failed"):
                with template_source.snapshot_source_set([source], staging_parent=root) as snapshots:
                    captured.append(snapshots[0].path.parent)
                    raise RuntimeError("extractor failed")
            self.assertFalse(captured[-1].exists())
            self.assertEqual(neighbor.read_text(encoding="utf-8"), "keep")

    def test_snapshot_rejects_reparse_staging_parent_when_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.mkdir()
            source = root / "example.png"
            source.write_bytes(b"\x89PNG\r\n\x1a\ncontent")
            link = root / "staging-link"
            try:
                link.symlink_to(target, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink unavailable: {exc}")
            with self.assertRaisesRegex(template_source.TemplateSourceError, "unsafe_staging_parent"):
                with template_source.snapshot_source_set([source], staging_parent=link):
                    pass

    def test_snapshot_revalidates_source_identity_before_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "example.png"
            target = root / "redirected.png"
            source.write_bytes(b"\x89PNG\r\n\x1a\noriginal")
            target.write_bytes(b"\x89PNG\r\n\x1a\nredirected")
            original_inspect = template_source.inspect_source_set

            def inspect_then_replace(paths):
                result = original_inspect(paths)
                os.replace(target, source)
                return result

            template_source.inspect_source_set = inspect_then_replace
            try:
                with self.assertRaisesRegex(
                    template_source.TemplateSourceError,
                    "source_changed_during_snapshot",
                ):
                    with template_source.snapshot_source_set([source], staging_parent=root):
                        pass
            finally:
                template_source.inspect_source_set = original_inspect

    def test_snapshot_cleanup_fails_closed_when_staging_parent_is_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging_parent = root / "staging"
            staging_parent.mkdir()
            source = root / "example.png"
            source.write_bytes(b"\x89PNG\r\n\x1a\ncontent")
            attacker = root / "attacker"
            attacker.mkdir()
            with template_source.snapshot_source_set([source], staging_parent=staging_parent) as snapshots:
                owned = snapshots[0].path.parent
                backup = root / "staging-backup"
                os.rename(staging_parent, backup)
                staging_parent.mkdir()
                (staging_parent / "sentinel.txt").write_text("keep", encoding="utf-8")
            self.assertTrue((root / "staging-backup" / owned.name).is_dir())
            self.assertFalse((attacker / owned.name).exists())
            self.assertTrue((staging_parent / "sentinel.txt").is_file())

    def test_post_copy_filesystem_errors_are_path_free_template_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "example.png"
            source.write_bytes(b"\x89PNG\r\n\x1a\ncontent")
            original_hash = template_source._hash_file

            def fail_with_absolute_path(path):
                raise OSError(f"permission denied: {Path(path).resolve()}")

            template_source._hash_file = fail_with_absolute_path
            try:
                with self.assertRaises(template_source.TemplateSourceError) as raised:
                    with template_source.snapshot_source_set([source], staging_parent=root):
                        pass
            finally:
                template_source._hash_file = original_hash
            self.assertEqual(str(raised.exception), "snapshot_filesystem_error")
            self.assertNotIn(str(root), str(raised.exception))

    def test_staging_parent_identity_setup_errors_are_path_free(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "example.png"
            source.write_bytes(b"\x89PNG\r\n\x1a\ncontent")
            original_identity = template_source._identity

            def fail_with_absolute_path(path):
                raise OSError(f"identity lookup failed: {Path(path).resolve()}")

            template_source._identity = fail_with_absolute_path
            try:
                with self.assertRaises(template_source.TemplateSourceError) as raised:
                    with template_source.snapshot_source_set([source], staging_parent=root):
                        pass
            finally:
                template_source._identity = original_identity
            self.assertEqual(str(raised.exception), "unsafe_staging_parent")
            self.assertNotIn(str(root), str(raised.exception))

    def test_snapshot_directory_creation_errors_are_path_free(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "example.png"
            source.write_bytes(b"\x89PNG\r\n\x1a\ncontent")
            original_mkdtemp = template_source.tempfile.mkdtemp

            def fail_with_absolute_path(*args, **kwargs):
                raise OSError(f"temporary directory failed: {root.resolve()}")

            template_source.tempfile.mkdtemp = fail_with_absolute_path
            try:
                with self.assertRaises(template_source.TemplateSourceError) as raised:
                    with template_source.snapshot_source_set([source], staging_parent=root):
                        pass
            finally:
                template_source.tempfile.mkdtemp = original_mkdtemp
            self.assertEqual(str(raised.exception), "snapshot_filesystem_error")
            self.assertNotIn(str(root), str(raised.exception))

    def test_owned_identity_setup_errors_are_path_free_and_cleanup_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "example.png"
            source.write_bytes(b"\x89PNG\r\n\x1a\ncontent")
            original_identity = template_source._identity
            calls = 0

            def fail_on_owned_identity(path):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError(f"owned identity failed: {Path(path).resolve()}")
                return original_identity(path)

            template_source._identity = fail_on_owned_identity
            try:
                with self.assertRaises(template_source.TemplateSourceError) as raised:
                    with template_source.snapshot_source_set([source], staging_parent=root):
                        pass
            finally:
                template_source._identity = original_identity
            self.assertEqual(str(raised.exception), "snapshot_filesystem_error")
            self.assertNotIn(str(root), str(raised.exception))
            snapshots = list(root.glob("codex-template-snapshot-*"))
            self.assertEqual(len(snapshots), 1)


if __name__ == "__main__":
    unittest.main()
