#!/usr/bin/env python3
"""Finalize one verified book package in a deterministic, auditable order.

The Vault and Desktop library are distinct outcomes.  A Local REST failure is
reported separately and never causes a direct filesystem write into the Vault.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path

import export_publication_bundle as exporter
import publish_manuscript_version as publisher
import render_manuscript
import validate_manuscript


@dataclass(frozen=True)
class FinalizeRequest:
    source_version_dir: Path
    config_path: Path
    vault_relative_version_dir: str
    publication_root: Path
    project_destination_root: str
    vault_path: Path
    base_url: str | None = None


def _resolve_local_rest_config(path: Path) -> Path:
    """Accept the public runtime.json contract without exposing its secrets."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    rest_path = payload.get("restDataPath") if isinstance(payload, dict) else None
    if rest_path:
        resolved = Path(str(rest_path))
        if not resolved.is_file():
            raise ValueError("local_rest_config_missing")
        return resolved
    if path.is_file() and path.name == "data.json":
        return path
    raise ValueError("runtime_config_missing_rest_data_path")


def _validate_and_render(request: FinalizeRequest) -> None:
    version = request.source_version_dir.resolve()
    manuscript = version / "manuscript.json"
    manifest = version / "asset-manifest.json"
    report = version / "asset-validation.json"
    if validate_manuscript.main(["validate_manuscript.py", str(manuscript), str(manifest), str(report)]) != 0:
        raise ValueError("validation_not_ready")
    render_manuscript.main(manuscript, version)


def finalize_publication(request: FinalizeRequest) -> dict:
    """Validate -> native render -> Vault attempt -> Desktop export, in that order."""

    _validate_and_render(request)
    vault_status = "not_published"
    publication_error = None
    try:
        publication = publisher.publish_version(
            _resolve_local_rest_config(request.config_path),
            request.source_version_dir,
            request.vault_relative_version_dir,
            request.base_url,
        )
        vault_status = str(publication.get("status") or "unknown")
    except Exception as error:  # Local REST is a separately reported outcome.
        vault_status = "publication_failed"
        publication_error = type(error).__name__

    desktop = exporter.export_publication_bundle(exporter.ExportRequest(
        source_version_dir=request.source_version_dir,
        publication_root=request.publication_root,
        project_destination_root=request.project_destination_root,
        vault_path=request.vault_path,
    ))
    desktop_status = str(desktop.get("status") or "export_failed")
    result = {
        "status": "finalized" if vault_status == "published" else "finalized_with_publication_failure",
        "vault_publication_status": vault_status,
        "desktop_export_status": desktop_status,
        "source_version": request.source_version_dir.name,
        "profile": "book_a4",
    }
    if publication_error:
        result["vault_publication_error_type"] = publication_error
    result.update({key: value for key, value in desktop.items() if key in {"latest_path", "history_path"}})
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Finalize one validated Book A4 version.")
    parser.add_argument("--source-version-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--vault-relative-version-dir", required=True)
    parser.add_argument("--publication-root", type=Path, required=True)
    parser.add_argument("--project-destination-root", required=True)
    parser.add_argument("--vault-path", type=Path, required=True)
    parser.add_argument("--base-url")
    args = parser.parse_args(argv)
    try:
        result = finalize_publication(FinalizeRequest(
            source_version_dir=args.source_version_dir,
            config_path=args.config,
            vault_relative_version_dir=args.vault_relative_version_dir,
            publication_root=args.publication_root,
            project_destination_root=args.project_destination_root,
            vault_path=args.vault_path,
            base_url=args.base_url,
        ))
    except Exception as error:
        print(json.dumps({"status": "failed", "code": "finalization_failed", "error": type(error).__name__}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
