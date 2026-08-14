#!/usr/bin/env python3
"""Generate a hash-complete lock file from a verified wheel directory."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import zipfile
from email import message_from_bytes
from pathlib import Path


_PINNED_REQUIREMENT = re.compile(
    r"^\s*([A-Za-z0-9][A-Za-z0-9_.-]*)\s*==\s*([^\s;#]+)"
)


def canonicalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_direct_requirements(path: Path) -> dict[str, str]:
    requirements: dict[str, str] = {}
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith(("-", "--")):
            continue
        match = _PINNED_REQUIREMENT.match(line)
        if not match:
            raise ValueError(
                f"requirements line {line_number} must use an exact == pin: {raw_line}"
            )
        name, version = match.groups()
        canonical = canonicalize_name(name)
        previous = requirements.get(canonical)
        if previous is not None and previous != version:
            raise ValueError(f"duplicate direct requirement with conflicting version: {name}")
        requirements[canonical] = version
    if not requirements:
        raise ValueError("requirements file contains no direct requirements")
    return requirements


def wheel_identity(path: Path) -> tuple[str, str]:
    if path.suffix.lower() != ".whl":
        raise ValueError(f"non-wheel file in wheel directory: {path.name}")
    try:
        with zipfile.ZipFile(path) as archive:
            metadata_name = next(
                name
                for name in archive.namelist()
                if name.endswith(".dist-info/METADATA")
            )
            message = message_from_bytes(archive.read(metadata_name))
    except (StopIteration, OSError, zipfile.BadZipFile) as error:
        raise ValueError(f"invalid wheel metadata: {path.name}") from error
    name = message.get("Name")
    version = message.get("Version")
    if not name or not version:
        raise ValueError(f"wheel metadata lacks Name or Version: {path.name}")
    return canonicalize_name(name), version


def render_sorted_hash_entries(
    grouped: dict[tuple[str, str], list[str]],
) -> str:
    blocks: list[str] = []
    for (name, version), hashes in sorted(grouped.items()):
        lines = [f"{name}=={version} \\"]
        for index, digest in enumerate(sorted(set(hashes))):
            suffix = " \\" if index < len(set(hashes)) - 1 else ""
            lines.append(f"    --hash=sha256:{digest}{suffix}")
        blocks.append("\n".join(lines))
    return (
        "# Generated from verified Windows CPython 3.12 wheels.\n"
        "# Regenerate with ci/generate-requirements-lock.py.\n\n"
        + "\n\n".join(blocks)
        + "\n"
    )


def build_lock(wheels: list[Path], direct: dict[str, str]) -> str:
    if not wheels:
        raise ValueError("wheel set is empty")
    grouped: dict[tuple[str, str], list[str]] = {}
    versions_by_name: dict[str, set[str]] = {}
    for wheel in sorted(wheels):
        identity = wheel_identity(wheel)
        name, version = identity
        versions_by_name.setdefault(name, set()).add(version)
        grouped.setdefault(identity, []).append(
            hashlib.sha256(wheel.read_bytes()).hexdigest()
        )
    duplicate_versions = {
        name: versions
        for name, versions in versions_by_name.items()
        if len(versions) > 1
    }
    if duplicate_versions:
        details = ", ".join(
            f"{name}: {sorted(versions)}"
            for name, versions in sorted(duplicate_versions.items())
        )
        raise ValueError(f"duplicate versions for one canonical name: {details}")
    resolved = {name: versions.pop() for name, versions in versions_by_name.items()}
    missing = sorted(
        f"{name}=={version}"
        for name, version in direct.items()
        if resolved.get(name) != version
    )
    if missing:
        raise ValueError(f"missing direct requirement(s): {', '.join(missing)}")
    return render_sorted_hash_entries(grouped)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_requirements", type=Path)
    parser.add_argument("wheel_directory", type=Path)
    parser.add_argument("output_lock", type=Path)
    args = parser.parse_args(argv)
    try:
        direct = parse_direct_requirements(args.input_requirements)
        wheels = [
            path
            for path in args.wheel_directory.iterdir()
            if path.is_file()
        ]
        lock = build_lock(wheels, direct)
        args.output_lock.parent.mkdir(parents=True, exist_ok=True)
        args.output_lock.write_text(lock, encoding="utf-8", newline="\n")
    except (OSError, ValueError) as error:
        print(f"lock generation failed: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
