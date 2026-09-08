"""Register approved custom templates through Obsidian Local REST only."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from save_via_obsidian_rest import list_vault_directory, read_vault_file, save_and_verify
from template_candidate_state import load_active_candidate
from template_model import Template, candidate_id_for_inputs
from validate_template_candidate import validate_candidate


_SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
_ALLOWLIST = {"template.json", "source-manifest.json", "source-analysis.json", "preview-content.json"}
_MAX_JSON_BYTES = 4 * 1024 * 1024
_MAX_SNAPSHOT_BYTES = 8 * 1024 * 1024


@contextmanager
def _registration_lock(candidate_id: str):
    if not isinstance(candidate_id, str) or not _SAFE_ID.fullmatch(candidate_id):
        raise ValueError("unsafe_template_id")
    root = Path(os.environ.get("CODEX_OBSIDIAN_STATE_ROOT", Path(os.environ.get("LOCALAPPDATA", Path.home())) / "CodexObsidianManuscript")) / "locks"
    path = root / f"template-{candidate_id}.lock"
    _guard_lock_path(path)
    root.mkdir(parents=True, exist_ok=True)
    handle = None
    try:
        for _ in range(100):
            _guard_lock_path(path)
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
            _guard_lock_path(path)
            try:
                path.unlink()
            except FileNotFoundError:
                pass


def _next_version(names: list[str] | None) -> str:
    used = []
    for name in names or []:
        match = re.fullmatch(r"t0\.(\d+)", name.removesuffix("/")) if isinstance(name, str) else None
        if match:
            used.append(int(match.group(1)))
    return f"t0.{max(used, default=0) + 1}"


def _is_reparse(info: os.stat_result) -> bool:
    return (stat.S_ISLNK(info.st_mode)
            or bool(getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT))


def _guard_lock_path(path: Path) -> None:
    """Check existing lexical ancestors and the leaf without following reparses."""
    if ".." in path.parts:
        raise ValueError("unsafe_template_lock_path")
    path = path.absolute()
    for entry in (*reversed(path.parents), path):
        try:
            info = entry.lstat()
        except FileNotFoundError:
            # A missing component has no existing descendants to inspect.
            return
        expected_type = stat.S_ISREG if entry == path else stat.S_ISDIR
        if _is_reparse(info) or not expected_type(info.st_mode):
            raise ValueError("unsafe_template_lock_path")


def _candidate_payloads(candidate_dir: str | Path) -> dict[str, bytes]:
    candidate = Path(candidate_dir)
    # Do not resolve first: normalization can erase a junction/symlink ancestor.
    if ".." in candidate.parts:
        raise ValueError("unsafe_template_candidate_path")
    candidate = candidate.absolute()
    try:
        for directory in (*reversed(candidate.parents), candidate):
            info = directory.lstat()
            if _is_reparse(info):
                raise ValueError("unsafe_template_candidate_path")
            if not stat.S_ISDIR(info.st_mode):
                raise ValueError("template_candidate_missing")
        files = {path.name: path for path in candidate.iterdir()}
        if set(files) != _ALLOWLIST:
            raise ValueError("template_candidate_allowlist_invalid")
        sizes = {}
        for name, path in files.items():
            info = path.lstat()
            if _is_reparse(info) or not stat.S_ISREG(info.st_mode):
                raise ValueError("template_candidate_allowlist_invalid")
            sizes[name] = info.st_size
        if any(size > _MAX_JSON_BYTES for size in sizes.values()) or sum(sizes.values()) > _MAX_SNAPSHOT_BYTES:
            raise ValueError("template_candidate_too_large")
        payloads = {}
        total = 0
        for name in sorted(files):
            # Bound the read itself as well as stat, including files that grow.
            limit = min(_MAX_JSON_BYTES, _MAX_SNAPSHOT_BYTES - total)
            with files[name].open("rb") as stream:
                content = stream.read(limit + 1)
            if len(content) > limit:
                raise ValueError("template_candidate_too_large")
            payloads[name] = content
            total += len(content)
        return payloads
    except FileNotFoundError as exc:
        raise ValueError("template_candidate_missing") from exc


def _payload_validation_hash(payloads: dict[str, bytes]) -> str:
    hashes = {name: hashlib.sha256(content).hexdigest() for name, content in payloads.items()}
    canonical = json.dumps(hashes, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_payloads(payloads: dict[str, bytes]) -> str:
    try:
        values = {name: json.loads(content.decode("utf-8")) for name, content in payloads.items()}
        if any(not isinstance(value, dict) for value in values.values()):
            raise ValueError("template_candidate_invalid")
        template = Template.from_dict(values["template.json"])
        analysis = values["source-analysis.json"]
        manifest = values["source-manifest.json"]
        if template.schema_version != 1 or template.template_profile != "custom_manuscript_template":
            raise ValueError("template_candidate_invalid")
        validation = validate_candidate({
            "safe_for_preview": analysis.get("status") == "safe_for_preview",
            "critical_unresolved": analysis.get("critical_unresolved", []),
        })
        if not validation["registration_ready"]:
            raise ValueError("template_preview_not_ready")
        if manifest != {"sources": analysis["source_manifest"], "evidence": analysis["evidence"]}:
            raise ValueError("template_candidate_manifest_mismatch")
        candidate_id = candidate_id_for_inputs({
            "schema_version": 1, "analysis": analysis, "template": template.to_dict(),
            "preview": values["preview-content.json"],
        })
        if values["template.json"].get("candidate_id") != candidate_id:
            raise ValueError("stale_candidate_approval")
        return candidate_id
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, AttributeError, KeyError) as exc:
        raise ValueError("template_candidate_invalid") from exc


def candidate_validation_hash(candidate_dir: str | Path) -> str:
    """Hash the validated four-file snapshot before activating/approving it.

    Pass this value to both candidate-state calls and ``register_candidate``.
    Registration re-reads once and verifies that exact snapshot before writing.
    """
    payloads = _candidate_payloads(candidate_dir)
    _validate_payloads(payloads)
    return _payload_validation_hash(payloads)


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
    payloads = _candidate_payloads(candidate_dir)
    if _payload_validation_hash(payloads) != validation_hash:
        raise ValueError("stale_candidate_approval")
    if _validate_payloads(payloads) != candidate_id:
        raise ValueError("stale_candidate_approval")
    transport = transport or _RestTransport()
    registry_root = f"_system/manuscript-template-registry/{candidate_id}"
    with _registration_lock(candidate_id):
        version = _next_version(transport.list(runtime_config, registry_root, base_url))
        remote_root = f"{registry_root}/{version}"
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
