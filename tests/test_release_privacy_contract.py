from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
PUBLISHER_SKILL = ROOT / "plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/SKILL.md"
PESTER_SCAN = ROOT / "tests/SecretScan.Tests.ps1"
ROUTER = ROOT / "plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/select_book_template.py"


class ReleasePrivacyContractTests(unittest.TestCase):
    @staticmethod
    def scan_candidate_archive(archive_path):
        findings = []
        forbidden_suffixes = (".pdf", ".docx", ".png", ".jpg", ".jpeg", ".webp", ".pem", ".key", ".pfx")
        markers = ("bearer ", "private key", "ghp_", "github_pat_", "sk-")
        with ZipFile(archive_path) as archive:
            for member in archive.infolist():
                name = member.filename.replace("\\", "/")
                lowered = name.lower()
                if name.startswith("/") or any(part == ".." for part in name.split("/")):
                    findings.append((name, "unsafe member path"))
                if lowered.endswith(forbidden_suffixes) or lowered.endswith("data.json"):
                    findings.append((name, "forbidden source or secret file"))
                if member.file_size <= 2 * 1024 * 1024:
                    content = archive.read(member).decode("utf-8", errors="ignore").lower()
                    if any(marker in content for marker in markers):
                        findings.append((name, "privacy marker"))
        return findings

    def test_pester_scan_uses_tracked_files_and_candidate_archive_list(self):
        text = PESTER_SCAN.read_text(encoding="utf-8")
        self.assertIn("git ls-files -z", text)
        self.assertIn("candidate", text.lower())
        self.assertIn("archive", text.lower())

    def test_privacy_contract_names_all_high_confidence_fixture_classes(self):
        text = PESTER_SCAN.read_text(encoding="utf-8").lower()
        for marker in (
            "bearer",
            "private key",
            "data.json",
            ".pem",
            ".key",
            "source pdf",
            "generated manuscript",
            "appdata",
        ):
            self.assertIn(marker, text)

    def test_fixture_literals_are_not_scanned_from_their_own_test_source(self):
        with tempfile.TemporaryDirectory(prefix="release-privacy-") as temporary:
            candidate = Path(temporary) / "candidate.zip"
            candidate.write_bytes(b"synthetic fixture")
            self.assertTrue(candidate.is_file())
            self.assertNotIn(str(candidate), PUBLISHER_SKILL.read_text(encoding="utf-8"))

    def test_candidate_archive_scan_checks_members_without_extracting(self):
        with tempfile.TemporaryDirectory(prefix="release-privacy-") as temporary:
            archive = Path(temporary) / "candidate.zip"
            with ZipFile(archive, "w", ZIP_DEFLATED) as writer:
                writer.writestr("preview.html", "safe preview")
                writer.writestr("assets/source.pdf", "source PDF")
                writer.writestr("metadata.json", "Authorization: Bearer synthetic-secret-value")
                writer.writestr("../escape.txt", "unsafe member")
                writer.writestr("C:/absolute.txt", "unsafe member")
                writer.writestr("secrets/data.json", '{"apiKey":"synthetic-secret-value"}')
            findings = self.scan_candidate_archive(archive)
            self.assertEqual(
                {reason for _, reason in findings},
                {"forbidden source or secret file", "privacy marker", "unsafe member path"},
            )

    def test_pester_contract_mentions_zip_member_preflight_and_profile_patterns(self):
        text = PESTER_SCAN.read_text(encoding="utf-8").lower()
        for marker in ("zipfile", "ziparchive", "users", "appdata", "additionalfiles"):
            self.assertIn(marker, text)

    def test_pressure_forward_scenario_keeps_conflicting_triggers_safe_and_explicit(self):
        cases = (
            ("new book default", "new book manuscript", None, 3, "default_new_book_a4"),
            ("explicit v3 with legacy wording", "legacy manuscript", 3, 3, "explicit_v3_request"),
            ("explicit v2", "new manuscript", 2, 2, "explicit_v2_request"),
            ("explicit legacy", "new manuscript", 1, 1, "explicit_legacy_request"),
        )
        with tempfile.TemporaryDirectory(prefix="release-pressure-") as temporary:
            result_path = Path(temporary) / "routing-results.json"
            results = []
            for label, prompt, explicit_version, version, reason in cases:
                command = [sys.executable, str(ROUTER), "--request-text", prompt]
                if explicit_version is not None:
                    command.extend(["--template-version", str(explicit_version)])
                completed = subprocess.run(
                    command,
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )
                result = json.loads(completed.stdout)
                results.append({"label": label, "result": result})
                self.assertEqual(result["template_version"], version, label)
                self.assertEqual(result["reason"], reason, label)
                self.assertEqual(result["output_profile"], "book_a4", label)
            result_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            self.assertTrue(result_path.is_file())
            self.assertEqual(result_path.parent, Path(temporary))


if __name__ == "__main__":
    unittest.main()
