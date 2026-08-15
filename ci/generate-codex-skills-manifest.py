"""Generate the deterministic Codex skill-pair manifest for a release tree."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SKILLS = (
    ("obsidian-manuscript-setup", Path("plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-setup")),
    ("obsidian-manuscript-publisher", Path("plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher")),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_manifest(root: Path) -> dict:
    skills = []
    for skill_id, source_root in SKILLS:
        absolute_root = root / source_root
        if not absolute_root.is_dir():
            raise SystemExit(f"skill source is missing: {source_root.as_posix()}")
        members = []
        for path in sorted(p for p in absolute_root.rglob("*") if p.is_file()):
            relative = path.relative_to(absolute_root).as_posix()
            members.append({"path": relative, "sha256": sha256(path)})
        skills.append(
            {
                "id": skill_id,
                "sourceRoot": source_root.as_posix(),
                "destination": skill_id,
                "files": members,
            }
        )
    return {"schemaVersion": 1, "skills": skills}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = build_manifest(args.root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
