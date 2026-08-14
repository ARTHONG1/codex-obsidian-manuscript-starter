import hashlib
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / "ci" / "generate-requirements-lock.py"
SPEC = importlib.util.spec_from_file_location(
    "generate_requirements_lock",
    GENERATOR_PATH,
)
generator = importlib.util.module_from_spec(SPEC)
try:
    SPEC.loader.exec_module(generator)
except FileNotFoundError:
    generator = None

DIRECT_PINS = (
    ("Pillow", "12.3.0"),
    ("reportlab", "4.4.3"),
    ("python-docx", "1.2.0"),
    ("pdfplumber", "0.11.9"),
    ("pypdfium2", "5.12.1"),
    ("pypdf", "5.9.0"),
)
FIXTURE_WHEELS = (
    ("Pillow", "12.3.0", "Pillow-12.3.0-cp312-cp312-win_amd64.whl"),
    ("reportlab", "4.4.3", "reportlab-4.4.3-cp312-cp312-win_amd64.whl"),
    ("python-docx", "1.2.0", "python_docx-1.2.0-py3-none-any.whl"),
    ("pdfplumber", "0.11.9", "pdfplumber-0.11.9-py3-none-any.whl"),
    ("pypdfium2", "5.12.1", "pypdfium2-5.12.1-py3-none-win_amd64.whl"),
    ("pypdf", "5.9.0", "pypdf-5.9.0-py3-none-any.whl"),
)


def _normalized_distribution(name: str) -> str:
    return name.replace("-", "_")


def _build_wheel_bytes(name: str, version: str, tag: str) -> bytes:
    distribution = _normalized_distribution(name)
    dist_info = f"{distribution}-{version}.dist-info"
    metadata = (
        "Metadata-Version: 2.1\n"
        f"Name: {name}\n"
        f"Version: {version}\n"
    )
    wheel = (
        "Wheel-Version: 1.0\n"
        "Generator: test-suite\n"
        "Root-Is-Purelib: true\n"
        f"Tag: {tag}\n"
    )
    record = (
        f"{dist_info}/METADATA,,\n"
        f"{dist_info}/WHEEL,,\n"
        f"{dist_info}/RECORD,,\n"
    )
    members = {
        f"{dist_info}/METADATA": metadata,
        f"{dist_info}/WHEEL": wheel,
        f"{dist_info}/RECORD": record,
    }
    with tempfile.SpooledTemporaryFile() as handle:
        with zipfile.ZipFile(handle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for member_name, payload in sorted(members.items()):
                info = zipfile.ZipInfo(member_name)
                info.date_time = (2020, 1, 1, 0, 0, 0)
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, payload)
        handle.seek(0)
        return handle.read()


def _write_wheel(
    directory: Path,
    filename: str,
    name: str,
    version: str,
    tag: str,
    *,
    content: bytes | None = None,
) -> Path:
    wheel_path = directory / filename
    wheel_path.write_bytes(content or _build_wheel_bytes(name, version, tag))
    return wheel_path


def _filename_tag(filename: str) -> str:
    return "-".join(filename.removesuffix(".whl").rsplit("-", 3)[-3:])


def logical_lock_entries(text: str) -> list[str]:
    return [
        block.replace("\\\n", " ")
        for block in text.split("\n\n")
        if block.strip() and not block.lstrip().startswith("#")
    ]


class RuntimeDependencyContractTests(unittest.TestCase):
    def test_runtime_renderer_dependencies_are_pinned(self):
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        for pin in (
            "Pillow==12.3.0",
            "reportlab==4.4.3",
            "python-docx==1.2.0",
            "pdfplumber==0.11.9",
            "pypdfium2==5.12.1",
            "pypdf==5.9.0",
        ):
            self.assertIn(pin, requirements)

    def test_development_requirements_include_runtime_dependencies(self):
        requirements = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
        self.assertIn("-r requirements.lock.txt", requirements)

    def test_runtime_lock_is_hash_complete_and_packaged_identically(self):
        root_lock = ROOT / "requirements.lock.txt"
        packaged_lock = (
            ROOT
            / "plugins/obsidian-manuscript-publisher/requirements.lock.txt"
        )
        self.assertEqual(root_lock.read_bytes(), packaged_lock.read_bytes())
        entries = logical_lock_entries(root_lock.read_text(encoding="utf-8"))
        self.assertTrue(entries)
        for entry in entries:
            self.assertRegex(entry, r"^[A-Za-z0-9_.-]+==[^\s]+")
            self.assertRegex(entry, r"--hash=sha256:[0-9a-f]{64}")
        lock_text = root_lock.read_text(encoding="utf-8")
        for name, version in DIRECT_PINS:
            self.assertRegex(
                lock_text,
                rf"(?m)^{generator.canonicalize_name(name)}=={version}(?:\s|\\)",
            )

    def test_lock_generator_rejects_missing_direct_requirement(self):
        generator = (
            ROOT / "ci" / "generate-requirements-lock.py"
        ).read_text(encoding="utf-8")
        self.assertIn("missing direct requirement", generator)
        self.assertIn("duplicate", generator.lower())

    def test_release_checklist_requires_real_wheelhouse_provenance_gate(self):
        release = (ROOT / "docs" / "RELEASE.md").read_text(encoding="utf-8")
        self.assertIn("TASK1_REQUIRE_REAL_WHEELHOUSE='1'", release)
        self.assertIn("TASK1_REAL_WHEELHOUSE", release)

    def test_exporter_documents_benign_root_file_policy_and_stable_errors(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        exporter = (
            ROOT
            / "plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/export_publication_bundle.py"
        ).read_text(encoding="utf-8")
        self.assertIn("desktop.ini", exporter)
        self.assertIn("Thumbs.db", exporter)
        self.assertIn("filesystem_error", exporter)
        self.assertIn("고정 버전", readme)

    def test_doctor_reports_actionable_missing_runtime_dependencies(self):
        for relative in ("bootstrap/doctor.ps1", "plugins/obsidian-manuscript-publisher/bootstrap/doctor.ps1"):
            doctor = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("python_dependency_missing", doctor)
            self.assertIn("six pinned document packages", doctor)


class RuntimeLockGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(generator, "generate-requirements-lock.py must exist")

    def _write_requirements(self, directory: Path) -> Path:
        path = directory / "requirements.txt"
        path.write_text(
            "\n".join(f"{name}=={version}" for name, version in DIRECT_PINS) + "\n",
            encoding="utf-8",
        )
        return path

    def _expected_lock(self, wheels: list[Path]) -> str:
        grouped: dict[tuple[str, str], set[str]] = {}
        for wheel in sorted(wheels):
            digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
            name, version = generator.wheel_identity(wheel)
            grouped.setdefault((name, version), set()).add(digest)
        blocks = []
        for name, version in sorted(grouped):
            hashes = sorted(grouped[(name, version)])
            lines = [f"{name}=={version} \\"]
            for index, digest in enumerate(hashes):
                suffix = " \\" if index < len(hashes) - 1 else ""
                lines.append(f"    --hash=sha256:{digest}{suffix}")
            blocks.append("\n".join(lines))
        return (
            "# Generated from verified Windows CPython 3.12 wheels.\n"
            "# Regenerate with ci/generate-requirements-lock.py.\n\n"
            + "\n\n".join(blocks)
            + "\n"
        )

    def test_rejects_incompatible_wheel_tags(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            wheel_dir = Path(temp_dir)
            rejected = (
                "Pillow-12.3.0-cp311-cp311-win_amd64.whl",
                "Pillow-12.3.0-cp313-cp313-win_amd64.whl",
                "Pillow-12.3.0-cp312-cp312-manylinux_x86_64.whl",
                "Pillow-12.3.0-cp312-cp312-macosx_11_0_arm64.whl",
                "Pillow-12.3.0-py3-none-linux_x86_64.whl",
                "Pillow-12.3.0-cp313-abi3-win_amd64.whl",
                "Pillow-12.3.0-cp312-abi3-manylinux_x86_64.whl",
            )
            for filename in rejected:
                _write_wheel(
                    wheel_dir,
                    filename,
                    "Pillow",
                    "12.3.0",
                    "cp312-cp312-win_amd64",
                )
                with self.assertRaisesRegex(ValueError, "unsupported wheel tag"):
                    generator.wheel_identity(wheel_dir / filename)
                (wheel_dir / filename).unlink()

    def test_rejects_filename_metadata_identity_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            wheel_dir = Path(temp_dir)
            mismatches = (
                (
                    "Pillow-12.3.0-cp312-cp312-win_amd64.whl",
                    "reportlab",
                    "12.3.0",
                    "filename distribution",
                ),
                (
                    "Pillow-12.3.0-cp312-cp312-win_amd64.whl",
                    "Pillow",
                    "12.3.1",
                    "filename version",
                ),
            )
            for filename, name, version, label in mismatches:
                with self.subTest(label=label):
                    wheel_path = _write_wheel(
                        wheel_dir,
                        filename,
                        name,
                        version,
                        "cp312-cp312-win_amd64",
                    )
                    with self.assertRaisesRegex(
                        ValueError, "wheel filename does not match metadata"
                    ):
                        generator.wheel_identity(wheel_path)
                    wheel_path.unlink()

    def test_accepts_real_windows_python_312_compatible_tags_through_identity(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            wheel_dir = Path(temp_dir)
            accepted = (
                ("Pillow", "12.3.0", "Pillow-12.3.0-cp312-cp312-win_amd64.whl"),
                ("Pillow", "12.3.0", "Pillow-12.3.0-cp312-abi3-win_amd64.whl"),
                ("cryptography", "50.0.0", "cryptography-50.0.0-cp311-abi3-win_amd64.whl"),
                ("cryptography", "50.0.0", "cryptography-50.0.0-cp37-abi3-win_amd64.whl"),
                ("python-docx", "1.2.0", "python_docx-1.2.0-py3-none-any.whl"),
                ("pypdfium2", "5.12.1", "pypdfium2-5.12.1-py3-none-win_amd64.whl"),
            )
            for name, version, filename in accepted:
                _write_wheel(
                    wheel_dir,
                    filename,
                    name,
                    version,
                    _filename_tag(filename),
                )
                self.assertEqual(
                    generator.wheel_identity(wheel_dir / filename),
                    (generator.canonicalize_name(name), version),
                )
                (wheel_dir / filename).unlink()

    def test_generator_cli_is_deterministic_and_preserves_direct_pins(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            wheel_dir = root / "wheelhouse"
            wheel_dir.mkdir()
            requirements_path = self._write_requirements(root)
            created: list[Path] = []
            for name, version, filename in FIXTURE_WHEELS:
                created.append(
                    _write_wheel(
                        wheel_dir,
                        filename,
                        name,
                        version,
                        _filename_tag(filename),
                    )
                )
            first_output = root / "first.lock.txt"
            second_output = root / "second.lock.txt"
            first = subprocess.run(
                [sys.executable, str(GENERATOR_PATH), str(requirements_path), str(wheel_dir), str(first_output)],
                capture_output=True,
                text=True,
                check=False,
            )
            second = subprocess.run(
                [sys.executable, str(GENERATOR_PATH), str(requirements_path), str(wheel_dir), str(second_output)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(first_output.read_bytes(), second_output.read_bytes())
            self.assertEqual(first_output.read_text(encoding="utf-8"), self._expected_lock(created))
            output_text = first_output.read_text(encoding="utf-8")
            for name, version in DIRECT_PINS:
                self.assertIn(f"{generator.canonicalize_name(name)}=={version}", output_text)

    def test_fixture_regeneration_gate_and_committed_lock_equality(self):
        """Always-on fixture proof; real wheelhouse reproduction is a separate maintainer command.

        Use TASK1_REAL_WHEELHOUSE with this module to regenerate from downloaded
        wheels when validating the committed hashes against real artifacts.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            wheel_dir = root / "wheelhouse"
            wheel_dir.mkdir()
            requirements_path = self._write_requirements(root)
            created = [
                _write_wheel(wheel_dir, filename, name, version, _filename_tag(filename))
                for name, version, filename in FIXTURE_WHEELS
            ]
            output_path = root / "fixture.lock.txt"
            result = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR_PATH),
                    str(requirements_path),
                    str(wheel_dir),
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                self._expected_lock(created),
            )
            self.assertEqual(
                (ROOT / "requirements.lock.txt").read_bytes(),
                (
                    ROOT
                    / "plugins/obsidian-manuscript-publisher/requirements.lock.txt"
                ).read_bytes(),
            )

    def test_duplicate_hashes_are_deduplicated_for_same_package_version(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            wheel_dir = root / "wheelhouse"
            wheel_dir.mkdir()
            requirements_path = self._write_requirements(root)
            for name, version, filename in FIXTURE_WHEELS:
                _write_wheel(
                    wheel_dir,
                    filename,
                    name,
                    version,
                    _filename_tag(filename),
                )
            duplicate_bytes = _build_wheel_bytes("python-docx", "1.2.0", "py3-none-any")
            _write_wheel(
                wheel_dir,
                "python_docx-1.2.0-1-py3-none-any.whl",
                "python-docx",
                "1.2.0",
                "py3-none-any",
                content=duplicate_bytes,
            )
            output_path = root / "duplicate.lock.txt"
            result = subprocess.run(
                [sys.executable, str(GENERATOR_PATH), str(requirements_path), str(wheel_dir), str(output_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            entry = next(
                entry for entry in logical_lock_entries(output_path.read_text(encoding="utf-8"))
                if entry.startswith("python-docx==1.2.0")
            )
            self.assertEqual(entry.count("--hash=sha256:"), 1)

    def test_real_wheelhouse_recreates_committed_lock_when_provided(self):
        wheelhouse = os.environ.get("TASK1_REAL_WHEELHOUSE")
        if not wheelhouse:
            if os.environ.get("TASK1_REQUIRE_REAL_WHEELHOUSE") == "1":
                self.fail(
                    "TASK1_REAL_WHEELHOUSE is required when real-wheelhouse "
                    "provenance is being certified"
                )
            self.skipTest("TASK1_REAL_WHEELHOUSE not set")
        wheelhouse_path = Path(wheelhouse)
        self.assertTrue(wheelhouse_path.is_dir(), "real wheelhouse must exist")
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "regenerated.lock.txt"
            result = subprocess.run(
                [sys.executable, str(GENERATOR_PATH), str(ROOT / "requirements.txt"), str(wheelhouse_path), str(output_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output_path.read_bytes(), (ROOT / "requirements.lock.txt").read_bytes())


if __name__ == "__main__":
    unittest.main()
