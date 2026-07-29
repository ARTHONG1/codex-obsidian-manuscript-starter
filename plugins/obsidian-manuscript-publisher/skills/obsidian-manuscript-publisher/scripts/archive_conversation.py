#!/usr/bin/env python3
"""Create one self-contained, append-only Obsidian bundle per conversation."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).parent))
from save_via_obsidian_rest import _relative_path, save_and_verify


CONVERSATION_KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _turn_markdown(turn: dict) -> str:
    return f"\n## {turn['role']} · {turn['id']}\n\n{turn.get('text', '')}\n"


def conversation_bundle(conversations_root: Path, conversation_key: str) -> Path:
    """Return a safe exact-key bundle path below the configured root."""
    if not CONVERSATION_KEY_PATTERN.fullmatch(str(conversation_key or "")):
        raise ValueError("invalid conversation_key")
    root = conversations_root.resolve()
    target = (root / conversation_key).resolve()
    try:
        target.relative_to(root)
    except ValueError as error:
        raise ValueError("conversation bundle must stay inside conversations root") from error
    return target


def _load_metadata(bundle: Path, conversation_key: str, title: str) -> dict:
    path = bundle / "metadata.json"
    if path.is_file():
        metadata = json.loads(path.read_text(encoding="utf-8"))
        if metadata.get("conversation_key") != conversation_key:
            raise ValueError("conversation metadata key mismatch")
        return metadata
    return {
        "conversation_key": conversation_key,
        "title": title,
        "turn_ids": [],
        "last_turn_id": None,
        "file_manifest": [],
        "asset_hashes": {},
    }


def _file_manifest(bundle: Path) -> list[str]:
    files = [path.relative_to(bundle).as_posix() for path in bundle.rglob("*") if path.is_file()]
    if "metadata.json" not in files:
        files.append("metadata.json")
    return sorted(files)


def _write_metadata(bundle: Path, metadata: dict) -> Path:
    path = bundle / "metadata.json"
    metadata["file_manifest"] = _file_manifest(bundle)
    path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def archive_conversation(
    conversations_root: Path,
    conversation_key: str,
    title: str,
    turns: list[dict],
) -> dict:
    if any(not str(turn.get("id", "")).strip() for turn in turns):
        raise ValueError("every turn requires an id")
    bundle = conversation_bundle(conversations_root, conversation_key)
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "assets").mkdir(exist_ok=True)
    metadata = _load_metadata(bundle, conversation_key, title)
    seen = set(metadata.get("turn_ids", []))
    new_turns = [turn for turn in turns if turn["id"] not in seen]
    archive_path = bundle / "conversation.md"
    if not archive_path.exists():
        archive_path.write_text(
            f"---\nconversation_key: {conversation_key}\ntitle: {title}\n---\n",
            encoding="utf-8",
        )
    if new_turns:
        with archive_path.open("a", encoding="utf-8", newline="\n") as handle:
            for turn in new_turns:
                handle.write(_turn_markdown(turn))
    ordered_ids = list(metadata.get("turn_ids", []))
    ordered_ids.extend(turn["id"] for turn in new_turns)
    metadata.update({
        "conversation_key": conversation_key,
        "title": title,
        "turn_ids": ordered_ids,
        "last_turn_id": ordered_ids[-1] if ordered_ids else None,
    })
    metadata_path = _write_metadata(bundle, metadata)
    return {
        "bundle_path": str(bundle),
        "archive_path": str(archive_path),
        "metadata_path": str(metadata_path),
        "new_turn_count": len(new_turns),
        "last_turn_id": metadata["last_turn_id"],
    }


def refresh_material_card(
    conversations_root: Path,
    conversation_key: str,
    title: str,
    sections: dict[str, list[str]],
) -> Path:
    """Write the editorial card beside its exact source conversation."""
    bundle = conversation_bundle(conversations_root, conversation_key)
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "assets").mkdir(exist_ok=True)
    metadata = _load_metadata(bundle, conversation_key, title)
    blocks = "\n\n".join(
        f"## {heading}\n" + "\n".join(f"- {item}" for item in items)
        for heading, items in sections.items()
    )
    path = bundle / "material-card.md"
    path.write_text(
        f"---\nconversation_key: {conversation_key}\narchive: conversation\n---\n\n[[conversation]]\n\n{blocks}\n",
        encoding="utf-8",
    )
    metadata.update({"conversation_key": conversation_key, "title": title})
    _write_metadata(bundle, metadata)
    return path


def publish_pair(
    config_path: Path,
    archive_path: Path,
    material_path: Path,
    archive_destination: str,
    material_destination: str,
    base_url: str | None = None,
) -> dict:
    """Publish the raw archive and its material card only after both verify."""
    save_and_verify(config_path, archive_destination, archive_path.read_bytes(), base_url)
    save_and_verify(config_path, material_destination, material_path.read_bytes(), base_url)
    return {"status": "archived", "published_files": 2}


def publish_bundle(
    config_path: Path,
    bundle: Path,
    vault_relative_bundle: str,
    base_url: str | None = None,
) -> dict:
    """Publish and verify every file in one exact conversation bundle."""
    bundle = bundle.resolve()
    if not bundle.is_dir():
        raise ValueError("bundle must be an existing directory")
    metadata_path = bundle / "metadata.json"
    if not metadata_path.is_file():
        raise ValueError("conversation bundle metadata is required")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not CONVERSATION_KEY_PATTERN.fullmatch(str(metadata.get("conversation_key", ""))):
        raise ValueError("conversation bundle metadata key is invalid")
    _write_metadata(bundle, metadata)

    destination_root = PurePosixPath(_relative_path(vault_relative_bundle))
    published: list[str] = []
    for source in sorted(path for path in bundle.rglob("*") if path.is_file()):
        relative = source.relative_to(bundle).as_posix()
        destination = (destination_root / relative).as_posix()
        save_and_verify(config_path, destination, source.read_bytes(), base_url)
        published.append(destination)
    return {
        "status": "archived",
        "conversation_key": metadata["conversation_key"],
        "published_files": len(published),
        "vault_relative_paths": published,
    }
