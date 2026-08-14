"""Deterministic runtime contract probe used by the Windows installer and doctor."""

from __future__ import annotations

import importlib
import importlib.metadata
import json
import re
import sys
from typing import Any


EXPECTED = {
    "Pillow": "12.3.0",
    "reportlab": "4.4.3",
    "python-docx": "1.2.0",
    "pdfplumber": "0.11.9",
    "pypdfium2": "5.12.1",
    "pypdf": "5.9.0",
}

MODULES = {
    "Pillow": "PIL",
    "reportlab": "reportlab",
    "python-docx": "docx",
    "pdfplumber": "pdfplumber",
    "pypdfium2": "pypdfium2",
    "pypdf": "pypdf",
}


def get_python_version() -> tuple[int, int]:
    return sys.version_info[:2]


def get_package_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for package in EXPECTED:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def import_runtime_modules() -> None:
    for module in MODULES.values():
        importlib.import_module(module)


def _base_result(requirements_hash: str | None = None) -> dict[str, Any]:
    result = {
        "ready": False,
        "reason": "unknown",
        "python": sys.executable,
        "python_version": f"{sys.version_info[0]}.{sys.version_info[1]}",
        "expected": dict(EXPECTED),
        "actual": {},
        "missing": [],
        "mismatched": {},
    }
    if requirements_hash is not None:
        result["requirements_hash"] = requirements_hash
    return result


def probe_runtime(requirements_hash: str | None = None) -> dict[str, Any]:
    if requirements_hash is not None and not re.fullmatch(r"[0-9a-f]{64}", requirements_hash):
        raise ValueError("requirements hash must be 64 lowercase hexadecimal characters")
    result = _base_result(requirements_hash)
    major, minor = get_python_version()
    result["python_version"] = f"{major}.{minor}"
    if (major, minor) != (3, 12):
        result["reason"] = "python_version_mismatch"
        return result

    actual = get_package_versions()
    actual = {package: actual.get(package) for package in EXPECTED}
    result["actual"] = actual
    missing = sorted(package for package, version in actual.items() if version is None)
    mismatched = {
        package: {"expected": EXPECTED[package], "actual": actual[package]}
        for package in EXPECTED
        if actual.get(package) is not None and actual[package] != EXPECTED[package]
    }
    result["missing"] = missing
    result["mismatched"] = mismatched
    if missing:
        result["reason"] = "package_missing"
        return result
    if mismatched:
        result["reason"] = "package_version_mismatch"
        return result

    try:
        import_runtime_modules()
    except Exception as exc:  # pragma: no cover - exact exception varies by broken install
        result["reason"] = "package_import_failed"
        result["import_error"] = type(exc).__name__
        return result

    result["ready"] = True
    result["reason"] = "ready"
    return result


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--requirements-hash")
    args = parser.parse_args()
    print(json.dumps(probe_runtime(args.requirements_hash), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
