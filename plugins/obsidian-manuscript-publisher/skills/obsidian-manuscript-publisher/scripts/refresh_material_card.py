#!/usr/bin/env python3
"""Atomically create or refresh one Obsidian material card per conversation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path


def _slug(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z가-힣]+", "-", value.strip()).strip("-")
    return slug[:60] or "conversation"


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".codex-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(temporary_name, path)
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def refresh_material_card(materials_dir: Path, conversation_key: str, title: str, content: str) -> Path:
    """Return the stable card path for one conversation, updating only that card."""
    if not conversation_key.strip():
        raise ValueError("conversation_key must not be empty")
    if not content.strip():
        raise ValueError("content_file must not be empty")

    materials_dir.mkdir(parents=True, exist_ok=True)
    index_path = materials_dir / "conversation-card-index.json"
    if index_path.exists():
        index = json.loads(index_path.read_text(encoding="utf-8"))
    else:
        index = {"schema": 1, "cards": {}}
    if not isinstance(index.get("cards"), dict):
        raise ValueError("conversation-card-index.json has an invalid cards mapping")

    cards = index["cards"]
    record = cards.get(conversation_key)
    if record:
        filename = record["filename"]
    else:
        fingerprint = hashlib.sha256(conversation_key.encode("utf-8")).hexdigest()[:10]
        filename = f"conversation-{_slug(title)}-{fingerprint}.md"
        cards[conversation_key] = {"filename": filename, "title": title}

    card_path = (materials_dir / filename).resolve()
    try:
        card_path.relative_to(materials_dir.resolve())
    except ValueError as error:
        raise ValueError("card path must stay inside materials_dir") from error

    _atomic_write(card_path, content)
    _atomic_write(index_path, json.dumps(index, ensure_ascii=False, indent=2) + "\n")
    return card_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--materials-dir", required=True)
    parser.add_argument("--conversation-key", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--content-file", required=True)
    arguments = parser.parse_args()

    content_path = Path(arguments.content_file)
    if not content_path.is_file():
        parser.error("--content-file must be an existing file")
    card_path = refresh_material_card(
        Path(arguments.materials_dir),
        arguments.conversation_key,
        arguments.title,
        content_path.read_text(encoding="utf-8"),
    )
    print(json.dumps({"status": "saved", "card_path": str(card_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
