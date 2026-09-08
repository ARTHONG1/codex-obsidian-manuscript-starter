"""Resolve approved custom templates from the Local REST registry."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from save_via_obsidian_rest import list_vault_directory, read_vault_file
from template_model import Template


_ROOT = "_system/manuscript-template-registry"
_SAFE_ID = re.compile(r"[a-z0-9][a-z0-9-]{1,63}")
_VERSION = re.compile(r"t0\.[1-9][0-9]{0,15}")
_FILES = {"template.json", "source-manifest.json", "source-analysis.json", "preview-content.json"}


def _safe_name(value: Any) -> bool:
    return (isinstance(value, str) and bool(value.strip()) and len(value) <= 240
            and not any(char in value for char in "<>\\/:%")
            and not any(ord(char) < 32 or ord(char) == 127 for char in value)
            and value not in {".", ".."})


def _directory_names(entries: Any, pattern: re.Pattern) -> list[str]:
    if entries is None:
        return []
    if not isinstance(entries, list):
        raise ValueError("unsafe_template_registry_path")
    names = []
    for entry in entries:
        # Local REST directory entries have one trailing slash; do not strip
        # arbitrary separators or normalize traversal supplied by the server.
        name = entry.removesuffix("/") if isinstance(entry, str) else ""
        if not pattern.fullmatch(name):
            raise ValueError("unsafe_template_registry_path")
        if name not in names:
            names.append(name)
    return names


def _read_json(raw: Any) -> dict:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (AttributeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("custom_template_snapshot_invalid") from exc
    if not isinstance(value, dict):
        raise ValueError("custom_template_snapshot_invalid")
    return value


def _validate_registry(record: dict, candidate_id: str, version: str) -> None:
    files = record.get("files")
    if (type(record.get("schema_version")) is not int or record["schema_version"] != 1
            or record.get("template_id") != candidate_id or record.get("version") != version
            or record.get("status") != "approved" or not _safe_name(record.get("display_name"))
            or not isinstance(files, dict) or set(files) != _FILES
            or any(not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest)
                   for digest in files.values())):
        raise ValueError("custom_template_registry_invalid")


class _RestTransport:
    def list(self, config, directory, base_url):
        return list_vault_directory(Path(config), directory, base_url)

    def read(self, config, path, base_url):
        return read_vault_file(Path(config), path, base_url)


def resolve_template(runtime_config: Any, name_or_id: str, base_url: str | None = None, *, version: str | None = None, transport: Any | None = None) -> dict:
    """Return registry metadata and the validated, hash-matched snapshot content.

    ``template`` preserves the registered JSON (including its candidate status);
    approval belongs to the registry, not a mutable field supplied by a caller.
    Only registry metadata is enumerated for display-name selection. Payloads
    are read once, for the selected version only, and never from a local Vault.
    An explicit ``version`` pins that snapshot; omission selects the latest.
    """
    if transport is None and not isinstance(runtime_config, (str, Path)):
        raise ValueError("custom_template_requires_local_rest")
    if not _safe_name(name_or_id):
        raise ValueError("unsafe_template_name")
    if version is not None and (not isinstance(version, str) or not _VERSION.fullmatch(version)):
        raise ValueError("unsafe_template_version")
    transport = transport or _RestTransport()
    candidates = _directory_names(transport.list(runtime_config, _ROOT, base_url), _SAFE_ID)
    by_id = name_or_id in candidates
    if by_id:
        candidates = [name_or_id]
    records = []
    for candidate_id in candidates:
        versions = _directory_names(transport.list(runtime_config, f"{_ROOT}/{candidate_id}", base_url), _VERSION)
        for record_version in versions:
            if version is not None and record_version != version:
                continue
            remote_root = f"{_ROOT}/{candidate_id}/{record_version}"
            value = _read_json(transport.read(runtime_config, f"{remote_root}/registry.json", base_url))
            if by_id or value.get("display_name") == name_or_id or value.get("template_id") == name_or_id:
                _validate_registry(value, candidate_id, record_version)
                records.append((value, remote_root))
    if not records:
        raise ValueError("custom_template_not_found")
    if len({record["template_id"] for record, _ in records}) != 1:
        raise ValueError("custom_template_ambiguous")
    record, remote_root = max(records, key=lambda item: int(item[0]["version"].split(".")[1]))
    payloads = {}
    for filename, expected_hash in record["files"].items():
        content = transport.read(runtime_config, f"{remote_root}/{filename}", base_url)
        if not isinstance(content, bytes) or hashlib.sha256(content).hexdigest() != expected_hash:
            raise ValueError("custom_template_snapshot_hash_mismatch")
        payloads[filename] = content
    template = _read_json(payloads["template.json"])
    try:
        model = Template.from_dict(template)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("custom_template_snapshot_invalid") from exc
    if (template.get("display_name") != record["display_name"]
            or template.get("candidate_id", record["template_id"]) != record["template_id"]
            or model.schema_version != 1 or model.template_profile != "custom_manuscript_template"):
        raise ValueError("custom_template_snapshot_invalid")
    return record | {"template": template, "snapshot_verified": True, "remote_root": remote_root}
