#!/usr/bin/env python3
"""Delete one exact conversation bundle through the local Obsidian REST API."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).parent))
from save_via_obsidian_rest import (
    _relative_path,
    delete_and_verify,
    list_vault_directory,
    read_vault_file,
)


CONVERSATION_KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _bundle_path(conversations_root: str, conversation_key: str) -> str:
    if not CONVERSATION_KEY_PATTERN.fullmatch(str(conversation_key or "")):
        raise ValueError("invalid conversation_key")
    root = PurePosixPath(_relative_path(conversations_root))
    target = root / conversation_key
    if target.parent != root:
        raise ValueError("conversation bundle must be an exact child of conversations root")
    return target.as_posix()


def _join(directory: str, child: str) -> str:
    return (PurePosixPath(directory) / child.rstrip("/")).as_posix()


def _list_files_recursive(
    config_path: Path,
    directory: str,
    base_url: str | None,
) -> list[str] | None:
    children = list_vault_directory(config_path, directory, base_url)
    if children is None:
        return None
    files: list[str] = []
    for child in children:
        child_path = _join(directory, child)
        if child.endswith("/"):
            nested = _list_files_recursive(config_path, child_path, base_url)
            if nested:
                files.extend(nested)
        else:
            files.append(child_path)
    return sorted(files)


def _sibling_probe(
    config_path: Path,
    conversations_root: str,
    conversation_key: str,
    base_url: str | None,
) -> tuple[str, str] | None:
    siblings = list_vault_directory(config_path, conversations_root, base_url) or []
    for sibling in siblings:
        if not sibling.endswith("/") or sibling.rstrip("/") == conversation_key:
            continue
        files = _list_files_recursive(config_path, _join(conversations_root, sibling), base_url) or []
        if files:
            payload = read_vault_file(config_path, files[0], base_url)
            if payload is not None:
                return files[0], hashlib.sha256(payload).hexdigest()
    return None


def remove_empty_bundle_directories(
    vault_root: Path,
    conversations_root: str,
    conversation_key: str,
) -> bool:
    """Remove only verified-empty directories inside one exact bundle."""
    relative_bundle = _bundle_path(conversations_root, conversation_key)
    vault = vault_root.resolve()
    target = (vault / Path(*PurePosixPath(relative_bundle).parts)).resolve()
    try:
        target.relative_to(vault)
    except ValueError as error:
        raise ValueError("physical conversation bundle must stay inside the vault") from error
    expected_parent = (vault / Path(*PurePosixPath(_relative_path(conversations_root)).parts)).resolve()
    if target.parent != expected_parent:
        raise ValueError("physical conversation bundle must be an exact child of conversations root")
    if not target.exists():
        return False
    entries = list(target.rglob("*"))
    unsafe = [path for path in entries if path.is_file() or path.is_symlink()]
    if unsafe:
        raise RuntimeError(f"conversation bundle is not empty: {unsafe[0]}")
    directories = sorted(
        (path for path in entries if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    )
    for directory in directories:
        directory.rmdir()
    target.rmdir()
    return True


def delete_conversation_bundle(
    config_path: Path,
    conversations_root: str,
    conversation_key: str,
    base_url: str | None = None,
    vault_root: Path | None = None,
) -> dict:
    root = _relative_path(conversations_root)
    bundle = _bundle_path(root, conversation_key)
    files = _list_files_recursive(config_path, bundle, base_url)
    if files is None:
        physical_bundle_removed = False
        if vault_root is not None:
            physical_bundle_removed = remove_empty_bundle_directories(vault_root, root, conversation_key)
        return {
            "status": "already_absent",
            "conversation_key": conversation_key,
            "deleted_files": [],
            "physical_bundle_removed": physical_bundle_removed,
        }

    metadata_path = f"{bundle}/metadata.json"
    metadata_payload = read_vault_file(config_path, metadata_path, base_url)
    if metadata_payload is None:
        raise RuntimeError("conversation metadata is unavailable; refusing deletion")
    metadata = json.loads(metadata_payload.decode("utf-8"))
    if metadata.get("conversation_key") != conversation_key:
        raise RuntimeError("conversation metadata key mismatch; refusing deletion")
    expected = {
        f"{bundle}/{PurePosixPath(relative).as_posix()}"
        for relative in metadata.get("file_manifest", [])
    }
    actual = set(files)
    if expected != actual:
        raise RuntimeError(
            "conversation metadata file manifest mismatch; refusing deletion: "
            f"expected={sorted(expected)} actual={sorted(actual)}"
        )
    metadata_hash = hashlib.sha256(metadata_payload).hexdigest()

    sibling = _sibling_probe(config_path, root, conversation_key, base_url)
    deleted: list[str] = []
    failures: list[str] = []
    sibling_files = [path for path in files if path != metadata_path]
    for path in sorted(sibling_files, key=lambda item: (item.count("/"), item), reverse=True):
        try:
            delete_and_verify(config_path, path, base_url)
            deleted.append(path)
        except Exception as error:
            failures.append(f"{path}: {error}")
    remaining = _list_files_recursive(config_path, bundle, base_url)
    if remaining:
        failures.extend(f"still present: {path}" for path in remaining)
    if sibling is not None:
        sibling_path, expected_hash = sibling
        sibling_payload = read_vault_file(config_path, sibling_path, base_url)
        if sibling_payload is None or hashlib.sha256(sibling_payload).hexdigest() != expected_hash:
            failures.append(f"unrelated conversation changed: {sibling_path}")
    current_metadata = read_vault_file(config_path, metadata_path, base_url)
    if current_metadata is None:
        failures.append("metadata disappeared before final deletion")
    elif hashlib.sha256(current_metadata).hexdigest() != metadata_hash:
        failures.append("metadata changed after snapshot")
    if failures:
        metadata_state = "metadata preserved; resume available" if current_metadata is not None else "metadata unavailable; resume blocked"
        raise RuntimeError(
            "partial_delete_failed (" + metadata_state + "): " + "; ".join(failures)
        )
    try:
        delete_and_verify(config_path, metadata_path, base_url)
        deleted.append(metadata_path)
    except Exception as error:
        metadata_remaining = read_vault_file(config_path, metadata_path, base_url)
        metadata_state = "metadata preserved; resume available" if metadata_remaining is not None else "metadata unavailable; resume blocked"
        raise RuntimeError(
            "partial_delete_failed (" + metadata_state + "): "
            f"{metadata_path}: {error}"
        ) from error
    physical_bundle_removed = False
    if vault_root is not None:
        physical_bundle_removed = remove_empty_bundle_directories(vault_root, root, conversation_key)
    return {
        "status": "deleted",
        "conversation_key": conversation_key,
        "deleted_files": sorted(deleted),
        "physical_bundle_removed": physical_bundle_removed,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--conversations-root", required=True)
    parser.add_argument("--conversation-key", required=True)
    parser.add_argument("--base-url")
    parser.add_argument("--vault-root")
    args = parser.parse_args()
    result = delete_conversation_bundle(
        Path(args.config),
        args.conversations_root,
        args.conversation_key,
        args.base_url,
        Path(args.vault_root) if args.vault_root else None,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
