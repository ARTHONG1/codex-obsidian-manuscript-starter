#!/usr/bin/env python3
"""Delete one exact conversation bundle through the local Obsidian REST API."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).parent))
import save_via_obsidian_rest as _rest
from save_via_obsidian_rest import (
    _relative_path,
    delete_and_verify,
    list_vault_directory,
    read_vault_file,
)


CONVERSATION_KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class _SnapshotError(RuntimeError):
    """Locally authored validation diagnostic, never a raw transport exception."""


def _safe_relative(value: str) -> str:
    if (not isinstance(value, str) or not value or "\\" in value or ":" in value
            or value != _relative_path(value)):
        raise ValueError("invalid journal/manifest relative path")
    return value


def _assert_state_path(path: Path) -> None:
    # Inspect before resolving: resolve() would hide junctions and symlinks.
    for entry in (*reversed(path.parents), path):
        try:
            info = os.lstat(entry)
        except FileNotFoundError:
            continue
        if (stat.S_ISLNK(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & 0x400):
            raise ValueError("deletion state must not contain a symlink or reparse point")
        if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
            raise ValueError("deletion state must not contain hard links")


@contextmanager
def _journal_lock(config_path: Path, bundle: str, base_url: str | None = None):
    identity = os.path.normcase(str(config_path.resolve()))
    if config_path.exists():
        endpoint = _rest._local_base_url(_rest._connection(config_path, base_url)[1])
    else:
        # No inferred default for config-free test transports. Real REST calls
        # still require the config; explicit overrides retain strict validation.
        endpoint = _rest._local_base_url(base_url) if base_url is not None else None
    key = hashlib.sha256(json.dumps([identity, bundle, endpoint]).encode()).hexdigest()
    state = Path(os.environ.get("CODEX_OBSIDIAN_STATE_ROOT",
        Path(os.environ.get("LOCALAPPDATA", Path.home())) / "CodexObsidianManuscript"))
    directory = Path(os.path.abspath(state)) / "deletion-journals"
    _assert_state_path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    lock_path = directory / f"{key}.lock"
    _assert_state_path(lock_path)
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(descriptor, "r+b") as stream:
        acquired = False
        deadline = time.monotonic() + 0.5
        try:
            while True:
                try:
                    stream.seek(0)
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                    break
                except OSError as error:
                    if time.monotonic() >= deadline:
                        raise RuntimeError("deletion_busy: another worker holds the bundle lock") from error
                    time.sleep(0.025)
            _assert_state_path(lock_path)
            journal_path = directory / f"{key}.json"
            _assert_state_path(journal_path)
            yield journal_path, key
        finally:
            if acquired:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    # Keep the lock inode: unlinking it lets waiters lock different files.


def _write_journal(path: Path, journal: dict) -> None:
    _assert_state_path(path)
    descriptor, name = tempfile.mkstemp(prefix=path.stem + "-", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(journal, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        for attempt in range(5):
            _assert_state_path(path)
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                # Windows readers without delete sharing can briefly deny the
                # atomic rename. Never advance to REST without durable intent.
                if attempt == 4:
                    raise
                time.sleep(0.05)
        if os.name != "nt":
            descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    finally:
        if temporary.exists():
            temporary.unlink()


def _validate_journal(journal: dict, key: str, config_hash: str) -> None:
    fields = {"owner", "key", "config_hash", "metadata_hash", "files", "intent", "verified", "sibling"}
    if (not isinstance(journal, dict) or set(journal) != fields
            or journal["owner"] != "codex-obsidian-delete-v1"
            or journal["key"] != key or journal["config_hash"] != config_hash
            or not re.fullmatch(r"[0-9a-f]{64}", str(journal["metadata_hash"]))):
        raise RuntimeError("invalid deletion journal identity or snapshot")
    for field in ("files", "intent", "verified"):
        values = journal[field]
        if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
            raise RuntimeError("invalid deletion journal file list")
        if values != sorted(set(values)):
            raise RuntimeError("invalid deletion journal file list")
        for value in values:
            _safe_relative(value)
    files, intent, verified = (set(journal[field]) for field in ("files", "intent", "verified"))
    if ("metadata.json" not in files or not verified <= intent <= files
            or ("metadata.json" in intent and not files - {"metadata.json"} <= verified)):
        raise RuntimeError("invalid deletion journal progress")
    sibling = journal["sibling"]
    if sibling is not None:
        if (not isinstance(sibling, list) or len(sibling) != 2
                or not re.fullmatch(r"[0-9a-f]{64}", str(sibling[1]))):
            raise RuntimeError("invalid deletion journal sibling")
        _safe_relative(sibling[0])


def _bundle_path(conversations_root: str, conversation_key: str) -> str:
    if not CONVERSATION_KEY_PATTERN.fullmatch(str(conversation_key or "")):
        raise ValueError("invalid conversation_key")
    root = PurePosixPath(_relative_path(conversations_root))
    target = root / conversation_key
    if target.parent != root:
        raise ValueError("conversation bundle must be an exact child of conversations root")
    return target.as_posix()


def _join(directory: str, child: str) -> str:
    name = child.removesuffix("/")
    if not name or name in {".", ".."} or any(c in name for c in "/\\:"):
        raise ValueError("invalid remote directory child; refusing traversal")
    return (PurePosixPath(directory) / name).as_posix()


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
    lexical_target = vault_root.absolute() / Path(*PurePosixPath(relative_bundle).parts)
    _assert_state_path(lexical_target)
    vault = vault_root.resolve()
    target = lexical_target.resolve()
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
    for entry in entries:
        _assert_state_path(entry)
    unsafe = [path for path in entries if path.is_file() or path.is_symlink()]
    if unsafe:
        raise RuntimeError(f"conversation bundle is not empty: {unsafe[0]}")
    directories = sorted(
        (path for path in entries if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    )
    for directory in directories:
        _assert_state_path(directory)
        directory.rmdir()
    _assert_state_path(lexical_target)
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
    with _journal_lock(config_path, bundle, base_url) as (journal_path, key):
        return _delete_locked(config_path, root, conversation_key, bundle,
                              base_url, vault_root, journal_path, key)


def _delete_locked(config_path, root, conversation_key, bundle, base_url,
                   vault_root, journal_path, key):
    config_hash = hashlib.sha256(config_path.read_bytes() if config_path.exists() else b"").hexdigest()
    journal = None
    if journal_path.exists():
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        _validate_journal(journal, key, config_hash)

    def remote_files():
        return set(_list_files_recursive(config_path, bundle, base_url) or [])

    actual = remote_files()
    metadata_path = f"{bundle}/metadata.json"
    if journal is None and actual:
        payload = read_vault_file(config_path, metadata_path, base_url)
        if payload is None:
            raise RuntimeError("conversation metadata is unavailable; refusing deletion")
        metadata = json.loads(payload.decode("utf-8"))
        if not isinstance(metadata, dict) or metadata.get("conversation_key") != conversation_key:
            raise RuntimeError("conversation metadata key mismatch; refusing deletion")
        manifest = metadata.get("file_manifest")
        if not isinstance(manifest, list):
            raise RuntimeError("conversation metadata file manifest mismatch")
        manifest = [_safe_relative(value) for value in manifest]
        if (len(set(manifest)) != len(manifest) or "metadata.json" not in manifest
                or {f"{bundle}/{value}" for value in manifest} != actual):
            raise RuntimeError("conversation metadata file manifest mismatch; refusing deletion")
        probe = _sibling_probe(config_path, root, conversation_key, base_url)
        journal = {
            "owner": "codex-obsidian-delete-v1", "key": key, "config_hash": config_hash,
            "metadata_hash": hashlib.sha256(payload).hexdigest(),
            "files": sorted(manifest), "intent": [], "verified": [],
            "sibling": [probe[0][len(root) + 1:], probe[1]] if probe else None,
        }
        _write_journal(journal_path, journal)

    def validate_snapshot():
        current = remote_files()
        expected = {f"{bundle}/{value}" for value in journal["files"]}
        intended = {f"{bundle}/{value}" for value in journal["intent"]}
        verified = {f"{bundle}/{value}" for value in journal["verified"]}
        extra = current - expected
        if extra:
            raise _SnapshotError("resume blocked; " + "; ".join(f"still present: {p}" for p in sorted(extra)))
        if expected - current - intended or current & verified:
            raise _SnapshotError("file manifest mismatch; resume blocked (unintended absence or reappeared file)")
        payload = read_vault_file(config_path, metadata_path, base_url)
        if payload is None:
            if "metadata.json" not in journal["intent"] or current:
                raise _SnapshotError("metadata disappeared before final deletion; resume blocked")
        elif hashlib.sha256(payload).hexdigest() != journal["metadata_hash"]:
            raise _SnapshotError("metadata changed after snapshot; resume blocked")
        elif sorted(json.loads(payload)["file_manifest"]) != journal["files"]:
            raise _SnapshotError("file manifest mismatch; resume blocked")
        sibling = journal["sibling"]
        if sibling:
            parts = PurePosixPath(sibling[0]).parts
            if len(parts) < 2 or parts[0] == conversation_key:
                raise _SnapshotError("invalid deletion journal sibling scope")
            sibling_path = f"{root}/{sibling[0]}"
            payload = read_vault_file(config_path, sibling_path, base_url)
            if payload is None or hashlib.sha256(payload).hexdigest() != sibling[1]:
                raise _SnapshotError(f"unrelated conversation changed: {sibling_path}; resume blocked")
        return current

    if journal is not None:
        try:
            validate_snapshot()
            order = sorted((p for p in journal["files"] if p != "metadata.json"),
                           key=lambda p: (p.count("/"), p), reverse=True) + ["metadata.json"]
            for relative in order:
                if relative in journal["verified"]:
                    continue
                current = validate_snapshot()
                path = f"{bundle}/{relative}"
                if path not in current:
                    # Only a persisted intent authorizes accepting an independently verified 404.
                    if relative not in journal["intent"] or read_vault_file(config_path, path, base_url) is not None:
                        raise _SnapshotError("file manifest mismatch; resume blocked")
                else:
                    if relative not in journal["intent"]:
                        journal["intent"] = sorted([*journal["intent"], relative])
                        _write_journal(journal_path, journal)
                    delete_and_verify(config_path, path, base_url)
                journal["verified"] = sorted([*journal["verified"], relative])
                _write_journal(journal_path, journal)
            validate_snapshot()
        except Exception as error:
            state = "journal preserved; resume blocked"
            try:
                validate_snapshot()
                state = "metadata preserved; resume available" if read_vault_file(config_path, metadata_path, base_url) is not None else "journal preserved; resume available"
            except Exception:
                pass
            detail = str(error) if isinstance(error, _SnapshotError) else type(error).__name__
            raise RuntimeError(f"partial_delete_failed ({state}): {detail}") from None

    physical_bundle_removed = False
    if vault_root is not None:
        physical_bundle_removed = remove_empty_bundle_directories(vault_root, root, conversation_key)
    if journal is not None:
        _assert_state_path(journal_path)
        journal_path.unlink()
    return {
        "status": "deleted" if journal is not None else "already_absent",
        "conversation_key": conversation_key,
        "deleted_files": sorted(f"{bundle}/{p}" for p in journal["verified"]) if journal else [],
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
