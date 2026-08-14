from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


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

    def test_lock_generator_rejects_missing_direct_requirement(self):
        generator = (
            ROOT / "ci" / "generate-requirements-lock.py"
        ).read_text(encoding="utf-8")
        self.assertIn("missing direct requirement", generator)
        self.assertIn("duplicate", generator.lower())

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


if __name__ == "__main__":
    unittest.main()
