"""Register approved custom templates through Obsidian Local REST only."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from save_via_obsidian_rest import list_vault_directory, read_vault_file, save_and_verify
from template_candidate_state import load_active_candidate


_SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
_ALLOWLIST = {"template.json", "source-manifest.json", "source-analysis.json", "preview-content.json"}


@contextmanager
def _registration_lock(candidate_id: str):
    root = Path(os.environ.get("CODEX_OBSIDIAN_STATE_ROOT", Path(os.environ.get("LOCALAPPDATA", Path.home())) / "CodexObsidianManuscript")) / "locks"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"template-{candidate_id}.lock"
    handle = None
    try:
        for _ in range(100):
            try:
                handle = path.open("x", encoding="ascii")
                break
            except FileExistsError:
                time.sleep(0.05)
        if handle is None:
            raise ValueError("template_registration_busy")
        yield
    finally:
        if handle is not None:
            handle.close()
            try:
                path.unlink()
            except FileNotFoundError:
                pass


def _next_version(names: list[str] | None) -> str:
    used = []
    for name in names or []:
        match = re.fullmatch(r"t0\.(\d+)", name)
        if match:
            used.append(int(match.group(1)))
    return f"t0.{max(used, default=0) + 1}"


def register_candidate(runtime_config: Any, candidate_dir: str | Path, approval: dict[str, Any], base_url: str | None = None, *, transport: Any | None = None) -> dict[str, str]:
    if not isinstance(approval, dict) or approval.get("candidate_id") != approval.get("approved_candidate_id"):
        raise ValueError("template_approval_required")
    if approval.get("status") != "preview_ready":
        raise ValueError("template_preview_not_ready")
    if transport is None and not isinstance(runtime_config, (str, Path)):
        raise ValueError("registration_requires_local_rest")
    conversation_key = approval.get("conversation_key")
    validation_hash = approval.get("validation_hash")
    state_root = os.environ.get("CODEX_OBSIDIAN_STATE_ROOT")
    active = load_active_candidate(conversation_key, state_root) if conversation_key else None
    if not active or active.get("status") != "approved" or active.get("candidate_id") != approval.get("candidate_id") or active.get("validation_hash") != validation_hash:
        raise ValueError("stale_candidate_approval")
    candidate_id = str(approval["candidate_id"])
    if not _SAFE_ID.fullmatch(candidate_id):
        raise ValueError("unsafe_template_id")
    candidate = Path(candidate_dir)
    if not candidate.is_dir():
        raise ValueError("template_candidate_missing")
    files = {path.name: path for path in candidate.iterdir() if path.is_file()}
    if set(files) != _ALLOWLIST:
        raise ValueError("template_candidate_allowlist_invalid")
    transport = transport or _RestTransport()
    registry_root = f"_system/manuscript-template-registry/{candidate_id}"
    with _registration_lock(candidate_id):
        version = _next_version(transport.list(runtime_config, registry_root, base_url))
        remote_root = f"{registry_root}/{version}"
        payloads = {name: files[name].read_bytes() for name in sorted(files)}
        hashes = {name: hashlib.sha256(content).hexdigest() for name, content in payloads.items()}
        for name, content in payloads.items():
            remote = f"{remote_root}/{name}"
            transport.save(runtime_config, remote, content, base_url)
            if transport.read(runtime_config, remote, base_url) != content:
                raise RuntimeError("template_registration_readback_failed")
        registry = {
            "schema_version": 1,
            "template_id": candidate_id,
            "display_name": json.loads(payloads["template.json"].decode("utf-8")).get("display_name", ""),
            "version": version,
            "status": "approved",
            "files": hashes,
        }
        registry_path = f"{remote_root}/registry.json"
        registry_bytes = (json.dumps(registry, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        transport.save(runtime_config, registry_path, registry_bytes, base_url)
        if transport.read(runtime_config, registry_path, base_url) != registry_bytes:
            raise RuntimeError("template_registration_readback_failed")
    return {"version": version, "remote_root": remote_root, "status": "registered"}


class _RestTransport:
    def list(self, config, directory, base_url):
        return list_vault_directory(Path(config), directory, base_url)

    def save(self, config, path, content, base_url):
        return save_and_verify(Path(config), path, content, base_url)

    def read(self, config, path, base_url):
        return read_vault_file(Path(config), path, base_url)
