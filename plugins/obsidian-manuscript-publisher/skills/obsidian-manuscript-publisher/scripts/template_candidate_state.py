"""Atomic, non-secret approval state for template candidates."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


_SAFE_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,100}$")


def _state_directory(conversation_key: str, root: str | Path | None) -> Path:
    if not isinstance(conversation_key, str) or not _SAFE_KEY.fullmatch(conversation_key):
        raise ValueError("unsafe_conversation_key")
    base = Path(root) if root is not None else Path(os.environ.get("LOCALAPPDATA", Path.home())) / "CodexObsidianManuscript" / "template-candidates"
    return base / conversation_key


def _write(directory: Path, payload: dict[str, Any]) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "active.json"
    temporary = directory / f"active.{os.getpid()}.tmp"
    temporary.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    os.replace(temporary, target)
    return payload


def load_active_candidate(conversation_key: str, root: str | Path | None = None) -> dict[str, Any] | None:
    target = _state_directory(conversation_key, root) / "active.json"
    if not target.is_file():
        return None
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("candidate_state_invalid") from exc
    if not isinstance(payload, dict):
        raise ValueError("candidate_state_invalid")
    return payload


def activate_candidate(conversation_key: str, candidate_id: str, validation_hash: str, root: str | Path | None = None) -> dict[str, Any]:
    if not candidate_id or not validation_hash:
        raise ValueError("candidate_state_invalid")
    payload = {
        "schema_version": 1,
        "conversation_key": conversation_key,
        "candidate_id": candidate_id,
        "validation_hash": validation_hash,
        "status": "active",
    }
    return _write(_state_directory(conversation_key, root), payload)


def approve_candidate(conversation_key: str, candidate_id: str, validation_hash: str, root: str | Path | None = None) -> dict[str, Any]:
    active = load_active_candidate(conversation_key, root)
    if not active or active.get("candidate_id") != candidate_id or active.get("validation_hash") != validation_hash:
        raise ValueError("stale_candidate_approval")
    active = dict(active)
    active["status"] = "approved"
    return _write(_state_directory(conversation_key, root), active)
