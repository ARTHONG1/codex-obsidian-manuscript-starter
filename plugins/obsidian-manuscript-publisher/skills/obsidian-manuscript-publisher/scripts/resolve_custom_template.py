"""Resolve approved custom templates from the Local REST registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from save_via_obsidian_rest import list_vault_directory, read_vault_file


class _RestTransport:
    def list(self, config, directory, base_url):
        return list_vault_directory(Path(config), directory, base_url)

    def read(self, config, path, base_url):
        return read_vault_file(Path(config), path, base_url)


def resolve_template(runtime_config: Any, name_or_id: str, base_url: str | None = None, *, transport: Any | None = None) -> dict:
    if transport is None and not isinstance(runtime_config, (str, Path)):
        raise ValueError("custom_template_requires_local_rest")
    transport = transport or _RestTransport()
    root = "_system/manuscript-template-registry"
    candidates = transport.list(runtime_config, root, base_url) or []
    records = []
    for candidate_id in candidates:
        versions = transport.list(runtime_config, f"{root}/{candidate_id}", base_url) or []
        for version in versions:
            if not isinstance(version, str) or not version.startswith("t0."):
                continue
            raw = transport.read(runtime_config, f"{root}/{candidate_id}/{version}/registry.json", base_url)
            if raw is None:
                continue
            try:
                value = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if value.get("display_name") == name_or_id or value.get("template_id") == name_or_id:
                records.append(value)
    if not records:
        raise ValueError("custom_template_not_found")
    return sorted(records, key=lambda item: tuple(int(p) for p in str(item["version"]).split(".")[1:]))[-1]
