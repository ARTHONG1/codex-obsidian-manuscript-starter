from __future__ import annotations

import json
from pathlib import Path


def resolve_template(registry_root: str | Path, name_or_id: str) -> dict:
    root = Path(registry_root)
    records = []
    for record in root.glob("t0.*.json"):
        try:
            value = json.loads(record.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if value.get("display_name") == name_or_id or value.get("template_id") == name_or_id:
            records.append(value)
    if not records:
        raise ValueError("custom_template_not_found")
    return sorted(records, key=lambda item: tuple(int(p) for p in item["version"].split(".")[1:]))[-1]
