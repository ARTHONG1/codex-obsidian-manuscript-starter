"""Finalize custom manuscript output with independent Vault and Desktop outcomes."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import publish_manuscript_version as publisher
from render_custom_manuscript import render_custom_manuscript


def _desktop_stage(rendered: dict[str, str], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="custom-publication-", dir=str(destination.parent)))
    try:
        for key, source in rendered.items():
            if key not in {"markdown", "html", "pdf"} or not isinstance(source, str):
                continue
            source_path = Path(source)
            (stage / source_path.name).write_bytes(source_path.read_bytes())
        destination.mkdir(parents=True, exist_ok=True)
        for path in stage.iterdir():
            os.replace(path, destination / path.name)
    finally:
        for path in stage.glob("*"):
            path.unlink(missing_ok=True)
        stage.rmdir()


def finalize_custom_publication(
    data: dict[str, Any],
    output_root: str | Path,
    desktop_root: str | Path | None = None,
    runtime_config: str | Path | None = None,
    vault_relative_version_dir: str | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    root = Path(output_root)
    if not re.fullmatch(r"v0\.[1-9][0-9]*", root.name):
        raise ValueError("custom_version_required")
    root.mkdir(parents=True, exist_ok=True)
    rendered = render_custom_manuscript(data, root)
    report_path = root / "publication-validation.json"
    report = {
        "profile": "custom_manuscript",
        "status": "rendered",
        "vault_publication_status": "not_attempted",
        "desktop_export_status": "not_attempted",
        "files": {key: value for key, value in rendered.items() if key in {"markdown", "html", "pdf"}},
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if runtime_config is not None:
        if not vault_relative_version_dir:
            raise ValueError("custom_vault_destination_required")
        try:
            result = publisher.publish_version(Path(runtime_config), root, vault_relative_version_dir, base_url)
            report["vault_publication_status"] = str(result.get("status", "unknown"))
        except Exception as exc:
            report["vault_publication_status"] = "publication_failed"
            report["vault_publication_error_type"] = type(exc).__name__
    if desktop_root is not None:
        _desktop_stage(rendered, Path(desktop_root))
        report["desktop_export_status"] = "exported"
    report["status"] = "finalized" if report["vault_publication_status"] in {"published", "not_attempted"} else "finalized_with_publication_failure"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
