import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
PROBE_PATH = ROOT / "bootstrap" / "verify_python_runtime.py"
SPEC = importlib.util.spec_from_file_location("verify_python_runtime", PROBE_PATH)
probe = importlib.util.module_from_spec(SPEC)
try:
    SPEC.loader.exec_module(probe)
except FileNotFoundError:
    probe = None


class PythonRuntimeProbeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(probe, "verify_python_runtime.py must exist")

    def _versions(self, **overrides):
        values = {name: version for name, version in probe.EXPECTED.items()}
        values.update(overrides)
        return values

    def test_accepts_python_312_and_all_exact_packages(self):
        with patch.object(probe, "get_python_version", return_value=(3, 12)), patch.object(
            probe, "get_package_versions", return_value=self._versions()
        ), patch.object(probe, "import_runtime_modules"):
            result = probe.probe_runtime()
        self.assertTrue(result["ready"])
        self.assertEqual(result["reason"], "ready")
        self.assertEqual(result["missing"], [])

    def test_rejects_python_311_with_stable_reason(self):
        with patch.object(probe, "get_python_version", return_value=(3, 11)), patch.object(
            probe, "get_package_versions", return_value=self._versions()
        ):
            result = probe.probe_runtime()
        self.assertFalse(result["ready"])
        self.assertEqual(result["reason"], "python_version_mismatch")
        self.assertEqual(result["python_version"], "3.11")

    def test_reports_missing_docx_without_importing_runtime_modules(self):
        versions = self._versions()
        versions.pop("python-docx")
        with patch.object(probe, "get_python_version", return_value=(3, 12)), patch.object(
            probe, "get_package_versions", return_value=versions
        ), patch.object(probe, "import_runtime_modules") as importer:
            result = probe.probe_runtime()
        self.assertFalse(result["ready"])
        self.assertEqual(result["reason"], "package_missing")
        self.assertEqual(result["missing"], ["python-docx"])
        importer.assert_not_called()

    def test_reports_wrong_pillow_version_without_claiming_ready(self):
        with patch.object(probe, "get_python_version", return_value=(3, 12)), patch.object(
            probe, "get_package_versions", return_value=self._versions(Pillow="12.2.0")
        ), patch.object(probe, "import_runtime_modules") as importer:
            result = probe.probe_runtime()
        self.assertFalse(result["ready"])
        self.assertEqual(result["reason"], "package_version_mismatch")
        self.assertEqual(result["mismatched"], {"Pillow": {"expected": "12.3.0", "actual": "12.2.0"}})
        importer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
