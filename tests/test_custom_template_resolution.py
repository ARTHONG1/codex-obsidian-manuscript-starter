import hashlib
import json
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).parents[1] / "plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts"
sys.path.insert(0, str(SCRIPTS))
from resolve_custom_template import resolve_template

ROOT = "_system/manuscript-template-registry"


def encoded(value):
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


class MemoryRest:
    """REST boundary double; all tests use synthetic in-memory Vault files."""

    def __init__(self, trailing_slashes=False):
        self.files = {}
        self.reads = []
        self.trailing_slashes = trailing_slashes
        self.listings = {}

    def list(self, config, directory, base_url):
        if directory in self.listings:
            return self.listings[directory]
        prefix = directory + "/"
        return sorted({path[len(prefix):].split("/")[0] + ("/" if self.trailing_slashes else "")
                       for path in self.files if path.startswith(prefix)})

    def read(self, config, path, base_url):
        self.reads.append(path)
        return self.files.get(path)

    def add(self, template_id="c-one", version="t0.1", name="My template", template=None):
        remote = f"{ROOT}/{template_id}/{version}"
        template = template if template is not None else {
            "display_name": name, "status": "candidate", "schema_version": 1,
            "template_profile": "custom_manuscript_template", "candidate_id": template_id,
            "blocks": [{"component": "paragraphs", "section_id": "body"}],
        }
        payloads = {"template.json": encoded(template), "source-manifest.json": b'{"sources": []}',
                    "source-analysis.json": b'{"status": "safe_for_preview"}', "preview-content.json": b'{"marker": "preview"}'}
        record = {"schema_version": 1, "template_id": template_id, "version": version,
                  "display_name": name, "status": "approved",
                  "files": {name: hashlib.sha256(content).hexdigest() for name, content in payloads.items()}}
        self.files.update({f"{remote}/{name}": content for name, content in payloads.items()})
        self.files[f"{remote}/registry.json"] = encoded(record)
        return remote, record


class CustomTemplateResolutionTests(unittest.TestCase):
    def setUp(self):
        self.rest = MemoryRest()
        self.remote, self.record = self.rest.add()

    def resolve(self, name="My template"):
        return resolve_template({}, name, transport=self.rest)

    def update_record(self, **changes):
        self.record.update(changes)
        self.rest.files[f"{self.remote}/registry.json"] = encoded(self.record)

    def test_returns_verified_registered_bytes_and_compatible_metadata(self):
        result = self.resolve()
        for key, value in self.record.items():
            self.assertEqual(result[key], value)
        self.assertIs(result.get("snapshot_verified"), True)
        self.assertEqual(result["remote_root"], self.remote)
        self.assertEqual(result["template"], json.loads(self.rest.files[f"{self.remote}/template.json"]))
        self.assertEqual(set(self.rest.reads), {f"{self.remote}/{name}" for name in (*self.record["files"], "registry.json")})

    def test_real_rest_trailing_slashes_and_numeric_latest_version(self):
        self.rest.trailing_slashes = True
        self.rest.add(version="t0.9")
        remote, _ = self.rest.add(version="t0.10")
        result = self.resolve("c-one")
        self.assertEqual(result["version"], "t0.10")
        self.assertEqual(result["remote_root"], remote)

    def test_only_selected_snapshot_payload_is_read(self):
        self.rest.add(template_id="c-other", name="Other template")
        old_remote, _ = self.rest.add(version="t0.2")
        result = self.resolve()
        self.assertEqual(result["version"], "t0.2")
        self.assertFalse(any("c-other" in path and not path.endswith("registry.json") for path in self.rest.reads))
        self.assertNotIn(f"{self.remote}/template.json", self.rest.reads)
        self.assertIn(f"{old_remote}/template.json", self.rest.reads)

    def test_exact_old_version_is_selected_without_reading_newer_snapshot(self):
        newer, _ = self.rest.add(version="t0.2")
        # A broken newer registry must not defeat an explicit approved pin.
        self.rest.files[f"{newer}/registry.json"] = b"invalid"
        result = resolve_template({}, "c-one", version="t0.1", transport=self.rest)
        self.assertEqual(result["version"], "t0.1")
        self.assertEqual(result["remote_root"], self.remote)
        self.assertIs(result["snapshot_verified"], True)
        self.assertFalse(any(path.startswith(newer + "/") for path in self.rest.reads))

    def test_nonexistent_exact_version_never_falls_back_to_latest(self):
        with self.assertRaisesRegex(ValueError, "custom_template_not_found"):
            resolve_template({}, "c-one", version="t0.99", transport=self.rest)
        self.assertEqual(self.rest.reads, [])

    def test_unsafe_exact_version_is_rejected_before_reading_registry(self):
        for version in ("../t0.1", "t0.1/", "t0.1/../../secret", "t0.1\\secret",
                        "t0.1%2fsecret", "", "t0.0", "t0.01", 1, [], "t0.1\n"):
            with self.subTest(version=version):
                with self.assertRaisesRegex(ValueError, "unsafe_template_version"):
                    resolve_template({}, "c-one", version=version, transport=self.rest)
                self.assertEqual(self.rest.reads, [])

    def test_duplicate_display_names_are_ambiguous(self):
        self.rest.add(template_id="c-two")
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            self.resolve()
        self.assertFalse(any(path.endswith("template.json") for path in self.rest.reads))

    def test_explicit_id_does_not_read_other_template_records(self):
        self.rest.add(template_id="c-two", name="Other")
        self.resolve("c-one")
        self.assertFalse(any("c-two" in path for path in self.rest.reads))

    def test_each_missing_or_tampered_registered_file_fails_closed(self):
        for filename in self.record["files"]:
            for tampered in (None, b"tampered"):
                with self.subTest(filename=filename, tampered=tampered):
                    key = f"{self.remote}/{filename}"
                    original = self.rest.files[key]
                    self.rest.files[key] = tampered
                    with self.assertRaisesRegex(ValueError, "snapshot"):
                        self.resolve()
                    self.rest.files[key] = original

    def test_invalid_matching_metadata_is_not_skipped_for_older_valid_version(self):
        self.rest.add(version="t0.2")
        for changes in ({"status": "candidate"}, {"template_id": "../escape"},
                        {"version": "t0.99"}, {"display_name": "<script>"},
                        {"schema_version": 2}, {"files": {}},
                        {"files": {"../../secret": "0" * 64}}):
            with self.subTest(changes=changes):
                original = dict(self.record)
                self.update_record(**changes)
                with self.assertRaises(ValueError):
                    self.resolve("c-one")
                self.record = original
                self.update_record()

    def test_unsafe_rest_directory_entries_never_become_read_paths(self):
        for directory, entry in ((ROOT, "../escape/"), (ROOT, "c-one//"),
                                 (f"{ROOT}/c-one", "t0.1/../../escape"),
                                 (f"{ROOT}/c-one", "t0.1\\escape"),
                                 (f"{ROOT}/c-one", "t0.1%2fescape")):
            with self.subTest(entry=entry):
                self.rest.listings = {directory: [entry]}
                self.rest.reads.clear()
                with self.assertRaises(ValueError):
                    self.resolve()
                self.assertEqual(self.rest.reads, [])

    def test_untrusted_selection_is_rejected_before_rest_reads(self):
        for name in ("", "../escape", "C:\\Vault", "<script>", "bad\nname", None, []):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    self.resolve(name)
                self.assertEqual(self.rest.reads, [])

    def test_valid_hash_does_not_authorize_invalid_template(self):
        for template in ({"display_name": "My template", "blocks": [{"component": "script"}]},
                         {"display_name": "My template", "blocks": [], "url": "secret"},
                         {"display_name": "Different", "blocks": []},
                         {"display_name": "My template", "candidate_id": "c-two", "blocks": []}):
            with self.subTest(template=template):
                self.rest.add(template=template)
                with self.assertRaises(ValueError):
                    self.resolve()

    def test_malformed_selected_registry_cannot_fall_back_to_older_snapshot(self):
        remote, _ = self.rest.add(version="t0.2")
        self.rest.files[f"{remote}/registry.json"] = b"broken json"
        with self.assertRaises(ValueError):
            self.resolve("c-one")

    def test_unknown_template_and_non_rest_configuration_have_no_filesystem_fallback(self):
        with self.assertRaisesRegex(ValueError, "custom_template_not_found"):
            self.resolve("Unknown")
        with self.assertRaisesRegex(ValueError, "custom_template_requires_local_rest"):
            resolve_template({}, "My template")


if __name__ == "__main__":
    unittest.main()
