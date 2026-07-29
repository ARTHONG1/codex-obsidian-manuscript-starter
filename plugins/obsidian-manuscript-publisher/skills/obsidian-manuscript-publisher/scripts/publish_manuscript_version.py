#!/usr/bin/env python3
"""Publish a complete manuscript version to local Obsidian with byte verification."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

from save_via_obsidian_rest import _relative_path, save_and_verify


REPORT_NAME = "publication-validation.json"


def _write_report(version_dir: Path, report: dict) -> Path:
    report_path = version_dir / REPORT_NAME
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report_path


def publish_version(config_path: Path, local_version_dir: Path, vault_relative_version_dir: str, base_url: str | None = None) -> dict:
    if not local_version_dir.is_dir():
        raise ValueError("local_version_dir must be an existing directory")
    vault_root = _relative_path(vault_relative_version_dir)
    files = sorted(
        path for path in local_version_dir.rglob("*")
        if path.is_file() and path.name != REPORT_NAME
    )
    published: list[dict] = []
    try:
        for local_path in files:
            relative_path = local_path.relative_to(local_version_dir).as_posix()
            vault_path = str(PurePosixPath(vault_root) / relative_path)
            content = local_path.read_bytes()
            save_and_verify(config_path, vault_path, content, base_url)
            published.append({
                "local_path": relative_path,
                "vault_relative_path": vault_path,
                "sha256": hashlib.sha256(content).hexdigest(),
            })
    except Exception as error:
        _write_report(local_version_dir, {"status": "publication_failed", "files": published, "error": str(error)})
        raise

    report = {"status": "published", "files": published}
    report_path = _write_report(local_version_dir, report)
    report_vault_path = str(PurePosixPath(vault_root) / REPORT_NAME)
    save_and_verify(config_path, report_vault_path, report_path.read_bytes(), base_url)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--local-version-dir", required=True)
    parser.add_argument("--vault-relative-version-dir", required=True)
    parser.add_argument("--base-url")
    arguments = parser.parse_args()
    result = publish_version(
        Path(arguments.config),
        Path(arguments.local_version_dir),
        arguments.vault_relative_version_dir,
        arguments.base_url,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
