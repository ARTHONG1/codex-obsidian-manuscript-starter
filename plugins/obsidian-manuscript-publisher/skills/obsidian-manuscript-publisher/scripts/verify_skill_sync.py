#!/usr/bin/env python3
"""Compare or safely promote one Codex skill tree without copying generated files."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import uuid


EXCLUDED_NAMES = {"__pycache__", ".pytest_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def _included(path: Path) -> bool:
    return not any(part in EXCLUDED_NAMES for part in path.parts) and path.suffix.lower() not in EXCLUDED_SUFFIXES


def file_hashes(root: Path) -> dict[str, str]:
    if not root.is_dir():
        raise ValueError(f"skill tree is not a directory: {root}")
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and _included(path.relative_to(root))
    }


def compare(source: Path, destination: Path) -> dict:
    source_hashes = file_hashes(source)
    destination_hashes = file_hashes(destination) if destination.exists() else {}
    missing = sorted(set(source_hashes) - set(destination_hashes))
    extra = sorted(set(destination_hashes) - set(source_hashes))
    changed = sorted(key for key in set(source_hashes) & set(destination_hashes) if source_hashes[key] != destination_hashes[key])
    return {
        "status": "matched" if not missing and not extra and not changed else "different",
        "source_files": len(source_hashes),
        "destination_files": len(destination_hashes),
        "missing": missing,
        "extra": extra,
        "changed": changed,
    }


def promote(source: Path, destination: Path) -> dict:
    parent = destination.parent
    parent.mkdir(parents=True, exist_ok=True)
    staging = parent / f".{destination.name}.staging-{uuid.uuid4().hex}"
    backup = parent / f".{destination.name}.backup-{uuid.uuid4().hex}"
    try:
        shutil.copytree(source, staging)
        result = compare(source, staging)
        if result["status"] != "matched":
            raise ValueError("staged skill tree did not match its source")
        if destination.exists():
            destination.rename(backup)
        staging.rename(destination)
        comparison = compare(source, destination)
        return {**comparison, "status": "promoted", "backup": str(backup) if backup.exists() else None}
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        if not destination.exists() and backup.exists():
            backup.rename(destination)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path)
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--promote", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        repo_root = Path(__file__).resolve().parents[5]
        source = args.source or (repo_root / "bootstrap")
        destination = args.destination or (repo_root / "plugins" / "obsidian-manuscript-publisher" / "bootstrap")
        result = compare(source, destination)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["status"] == "matched" else 1
    if not args.source or not args.destination:
        parser.error("--source and --destination are required unless --check is specified")
    try:
        result = promote(args.source, args.destination) if args.promote else compare(args.source, args.destination)
    except Exception as error:
        print(json.dumps({"status": "failed", "code": "skill_sync_failed", "error": type(error).__name__}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

