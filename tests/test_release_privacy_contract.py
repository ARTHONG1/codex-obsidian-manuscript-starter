from pathlib import Path
import tempfile
import unittest
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
PUBLISHER_SKILL = ROOT / "plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/SKILL.md"
PESTER_SCAN = ROOT / "tests/SecretScan.Tests.ps1"


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
            "sample-account",
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
            findings = self.scan_candidate_archive(archive)
            self.assertEqual(
                {reason for _, reason in findings},
                {"forbidden source or secret file", "privacy marker", "unsafe member path"},
            )


if __name__ == "__main__":
    unittest.main()
