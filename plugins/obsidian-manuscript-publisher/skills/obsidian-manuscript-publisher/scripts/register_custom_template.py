from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def register_candidate(candidate: dict[str, Any], registry_root: str | Path) -> dict[str, str]:
    if candidate.get("candidate_id") != candidate.get("approved_candidate_id"):
        raise ValueError("template_approval_required")
    if candidate.get("status") != "preview_ready":
        raise ValueError("template_preview_not_ready")
    root = Path(registry_root)
    root.mkdir(parents=True, exist_ok=True)
    versions = sorted(root.glob("t0.*.json"))
    version = f"t0.{len(versions) + 1}"
    record = root / f"{version}.json"
    payload = {"template_id": candidate["candidate_id"], "display_name": candidate.get("display_name", ""), "version": version, "status": "approved"}
    record.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"version": version, "record": str(record)}
