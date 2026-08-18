from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "ci" / "build-release.ps1"
VERIFY = ROOT / "ci" / "verify-release.ps1"
PYTHON = Path(os.environ.get("PYTHON", os.sys.executable))


def run_powershell(script: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        *arguments,
    ]
    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8")


class ReleasePackageTests(unittest.TestCase):
    def test_build_creates_exactly_allowlisted_sorted_forward_slash_members_and_checksum(self):
        with tempfile.TemporaryDirectory(prefix="release-package-") as temporary:
            output = Path(temporary)
            result = run_powershell(
                BUILD,
                "-SourceRoot",
                str(ROOT),
                "-OutputRoot",
                str(output),
                "-Version",
                "0.6.0",
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            archive = output / "codex-obsidian-manuscript-starter-v0.6.0.zip"
            checksums = output / "SHA256SUMS"
            manifest = output / "release-manifest.json"
            self.assertTrue(archive.is_file())
            self.assertTrue(checksums.is_file())
            self.assertTrue(manifest.is_file())
            release_manifest = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(release_manifest["schemaVersion"], 1)
            self.assertEqual(release_manifest["version"], "0.6.0")
            self.assertEqual(release_manifest["tag"], "v0.6.0")
            self.assertEqual(release_manifest["archive"], archive.name)
            self.assertEqual(
                [entry["name"] for entry in release_manifest["files"]],
                sorted(entry["name"] for entry in release_manifest["files"]),
            )
            with ZipFile(archive) as package:
                names = [item.filename for item in package.infolist()]
                self.assertEqual(names, sorted(names))
                self.assertEqual(names, [name.replace("\\", "/") for name in names])
                self.assertEqual(len(names), len({name.casefold() for name in names}))
                self.assertIn("plugins/obsidian-manuscript-publisher/.codex-plugin/plugin.json", names)
                self.assertIn("docs/USAGE_GUIDE.md", names)
                self.assertIn("docs/RELEASE_NOTES_v0.6.0.md", names)
                self.assertNotIn("tests/test_release_package.py", names)
                contents = {name: package.read(name) for name in names}
                self.assertEqual(contents["dependencies.lock.json"], contents["bootstrap/dependencies.lock.json"])
                self.assertEqual(
                    contents["dependencies.lock.json"],
                    contents["plugins/obsidian-manuscript-publisher/bootstrap/dependencies.lock.json"],
                )
            checksum_line = checksums.read_text(encoding="utf-8").strip()
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            checksum_lines = checksums.read_text(encoding="ascii").splitlines()
            self.assertEqual(checksum_lines[0], f"{digest}  {archive.name}")
            self.assertEqual(
                checksum_lines[1],
                f"{hashlib.sha256(manifest.read_bytes()).hexdigest()}  {manifest.name}",
            )

    def test_verify_rejects_malicious_members_before_extraction(self):
        with tempfile.TemporaryDirectory(prefix="release-malicious-") as temporary:
            root = Path(temporary)
            archive = root / "malicious.zip"
            checksums = root / "SHA256SUMS"
            with ZipFile(archive, "w", ZIP_DEFLATED) as package:
                package.writestr("../escape.txt", "escape")
                package.writestr("C:/absolute.txt", "absolute")
                package.writestr("README.md", "safe")
                package.writestr("readme.md", "case collision")
                package.writestr("data.json", "{}")
                package.writestr("source.pdf", "pdf")
                package.writestr("private.pem", "key")
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            checksums.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
            extraction = root / "extract"
            result = run_powershell(
                VERIFY,
                "-Archive",
                str(archive),
                "-Checksums",
                str(checksums),
                "-TestRoot",
                str(extraction),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(extraction.exists())

    def test_verify_checks_checksum_and_clean_install(self):
        with tempfile.TemporaryDirectory(prefix="release-verify-") as temporary:
            root = Path(temporary)
            output = root / "output"
            build = run_powershell(
                BUILD,
                "-SourceRoot",
                str(ROOT),
                "-OutputRoot",
                str(output),
                "-Version",
                "0.6.0",
            )
            self.assertEqual(build.returncode, 0, build.stderr + build.stdout)
            archive = output / "codex-obsidian-manuscript-starter-v0.6.0.zip"
            checksums = output / "SHA256SUMS"
            extraction = root / "clean-install"
            verified = run_powershell(
                VERIFY,
                "-Archive",
                str(archive),
                "-Checksums",
                str(checksums),
                "-TestRoot",
                str(extraction),
            )
            self.assertEqual(verified.returncode, 0, verified.stderr + verified.stdout)
            self.assertTrue(extraction.is_dir())
            self.assertTrue(
                (extraction / "plugins/obsidian-manuscript-publisher/.codex-plugin/plugin.json").is_file()
            )

    def test_two_builds_have_identical_member_and_content_identity(self):
        with tempfile.TemporaryDirectory(prefix="release-reproducible-") as temporary:
            root = Path(temporary)
            identities = []
            for index in (1, 2):
                output = root / f"output-{index}"
                result = run_powershell(
                    BUILD,
                    "-SourceRoot",
                    str(ROOT),
                    "-OutputRoot",
                    str(output),
                    "-Version",
                    "0.6.0",
                )
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                with ZipFile(output / "codex-obsidian-manuscript-starter-v0.6.0.zip") as package:
                    identities.append(
                        [
                            (item.filename, hashlib.sha256(package.read(item.filename)).hexdigest())
                            for item in package.infolist()
                        ]
                    )
            self.assertEqual(identities[0], identities[1])

    def test_build_refuses_untracked_required_file(self):
        with tempfile.TemporaryDirectory(prefix="release-untracked-") as temporary:
            source = Path(temporary) / "source"
            shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns(".git", ".worktrees"))
            required = source / "README.md"
            required.write_text(required.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            result = run_powershell(
                BUILD,
                "-SourceRoot",
                str(source),
                "-OutputRoot",
                str(Path(temporary) / "output"),
                "-Version",
                "0.6.0",
            )
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
