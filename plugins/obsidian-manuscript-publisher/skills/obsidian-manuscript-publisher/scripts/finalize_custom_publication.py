from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from render_custom_manuscript import render_custom_manuscript


def finalize_custom_publication(data: dict[str, Any], output_root: str | Path, desktop_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    rendered = render_custom_manuscript(data, root)
    manifest = {"profile": "custom_manuscript", "status": "rendered", "vault_publication_status": "not_attempted", "desktop_export_status": "not_attempted", "files": rendered}
    (root / "publication-validation.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if desktop_root:
        destination = Path(desktop_root)
        destination.mkdir(parents=True, exist_ok=True)
        for source in rendered.values():
            shutil.copy2(source, destination / Path(source).name)
        manifest["desktop_export_status"] = "exported"
    return manifest
