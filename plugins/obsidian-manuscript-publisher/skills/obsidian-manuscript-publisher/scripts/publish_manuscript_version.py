#!/usr/bin/env python3
"""Publish a complete manuscript version to local Obsidian with byte verification."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import stat
import tempfile
from pathlib import Path, PurePosixPath

from save_via_obsidian_rest import (
    _relative_path,
    list_vault_directory,
    save_and_verify,
)


REPORT_NAME = "publication-validation.json"
BLOG_DIRECTORY = "02 Blog"
BOOK_DIRECTORY = "01 Manuscript"
BLOG_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VERSION_PATTERN = re.compile(r"^v0\.[1-9][0-9]*$")
APPROVED_ROOTS = {"Projects", "01 Projects", BLOG_DIRECTORY, BOOK_DIRECTORY}


def _report_bytes(report: dict) -> bytes:
    return (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _write_report(version_dir: Path, report: dict) -> Path:
    report_path = version_dir / REPORT_NAME
    handle, temporary_name = tempfile.mkstemp(prefix=f".{REPORT_NAME}.", suffix=".tmp", dir=version_dir)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(_report_bytes(report))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, report_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    return report_path


def _unsafe_link_reason(path: Path) -> str | None:
    """Return why *path* cannot be trusted as a publication root/entry."""
    metadata = os.lstat(path)
    if stat.S_ISLNK(metadata.st_mode):
        return "symbolic link"
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if getattr(metadata, "st_file_attributes", 0) & reparse_flag:
        return "reparse point"
    return None


def _assert_safe_version_root(version_dir: Path) -> None:
    reason = _unsafe_link_reason(version_dir)
    if reason is not None:
        raise ValueError(f"local_version_dir must not be a {reason}")


def _load_blog_renderer():
    renderer_path = Path(__file__).resolve().with_name("render_blog.py")
    spec = importlib.util.spec_from_file_location("obsidian_adaptive_blog_renderer", renderer_path)
    if spec is None or spec.loader is None:
        raise ValueError("adaptive blog renderer could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_book_validator():
    validator_path = Path(__file__).resolve().with_name("validate_manuscript.py")
    spec = importlib.util.spec_from_file_location("obsidian_book_a4_validator", validator_path)
    if spec is None or spec.loader is None:
        raise ValueError("book_a4 validator could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _version_files(version_dir: Path) -> list[Path]:
    entries = list(version_dir.rglob("*"))
    for path in entries:
        reason = _unsafe_link_reason(path)
        if reason is not None:
            raise ValueError(f"version directory must not contain a {reason}")
        if path.is_file() and path.name == REPORT_NAME and path.parent != version_dir:
            raise ValueError("nested publication-validation.json is forbidden")
    return sorted(
        path for path in entries
        if path.is_file() and path.name != REPORT_NAME
    )


def _blog_destination(vault_root: str) -> tuple[str, str] | None:
    parts = PurePosixPath(vault_root).parts
    positions = [index for index, part in enumerate(parts) if part == BLOG_DIRECTORY]
    if not positions:
        return None
    if len(positions) != 1:
        raise ValueError("adaptive_blog destination must contain one 02 Blog segment")
    position = positions[0]
    if not parts or parts[0] not in APPROVED_ROOTS:
        raise ValueError("publication destination is outside an approved publication root")
    if len(parts) != position + 3:
        raise ValueError("adaptive_blog destination must be 02 Blog/<topic-slug>/v0.N")
    slug, version = parts[position + 1 :]
    if not BLOG_SLUG_PATTERN.fullmatch(slug) or not VERSION_PATTERN.fullmatch(version):
        raise ValueError("adaptive_blog destination requires a safe slug and immutable v0.N version")
    return slug, version


def _book_destination(vault_root: str) -> str | None:
    parts = PurePosixPath(vault_root).parts
    positions = [index for index, part in enumerate(parts) if part == BOOK_DIRECTORY]
    if not positions:
        return None
    if len(positions) != 1 or not parts or parts[0] not in APPROVED_ROOTS or parts[-1] == BOOK_DIRECTORY or not VERSION_PATTERN.fullmatch(parts[-1]):
        if parts and parts[0] not in APPROVED_ROOTS:
            raise ValueError("publication destination is outside an approved publication root")
        raise ValueError("book_a4 destination must be below 01 Manuscript and end in an immutable v0.N version")
    return parts[-1]


def _assert_generic_destination(vault_root: str) -> None:
    parts = PurePosixPath(vault_root).parts
    forbidden = {".obsidian", ".trash", "_system"}
    if any(part in forbidden for part in parts):
        raise ValueError("publication destination contains a protected vault directory")
    if not parts or any(re.match(r"^[A-Za-z]:$", part) for part in parts):
        raise ValueError("publication destination must be vault-relative")
    if not VERSION_PATTERN.fullmatch(parts[-1]):
        raise ValueError("publication destination must end in immutable v0.N")
    if not parts or parts[0] not in APPROVED_ROOTS:
        raise ValueError("publication destination is outside an approved publication root")


def _safe_asset_output_path(value: object, *, profile: str) -> str:
    raw = str(value or "")
    parts = raw.split("/")
    path = PurePosixPath(raw)
    if (
        not raw
        or "\\" in raw
        or path.is_absolute()
        or not parts
        or parts[0] != "assets"
        or any(part in {"", ".", ".."} for part in parts)
        or re.match(r"^[A-Za-z]:", raw)
    ):
        raise ValueError(f"{profile} asset path must stay below the version-local assets directory")
    return path.as_posix()


def _validate_adaptive_blog_publication(version_dir: Path, files: list[Path], vault_root: str) -> None:
    blog_path = version_dir / "blog.json"
    destination = _blog_destination(vault_root)
    if not blog_path.is_file():
        if destination is not None:
            raise ValueError("adaptive_blog destination requires blog.json and a complete blog package")
        return

    blog = json.loads(blog_path.read_text(encoding="utf-8"))
    if blog.get("output_profile") != "adaptive_blog":
        raise ValueError("blog.json requires output_profile adaptive_blog")
    if destination is None:
        raise ValueError("adaptive_blog package must publish below 02 Blog/<topic-slug>/v0.N")
    if blog.get("slug") != destination[0]:
        raise ValueError("adaptive_blog destination slug must match blog.json slug")

    manifest_path = version_dir / "asset-manifest.json"
    if not manifest_path.is_file():
        raise ValueError("adaptive_blog asset-manifest.json is required")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assets = manifest.get("assets")
    if not isinstance(assets, list):
        raise ValueError("adaptive_blog asset manifest is invalid")

    expected_files = {
        "blog.json",
        "asset-manifest.json",
        "blog-validation.json",
        "blog.md",
        "blog.html",
    }
    for asset in assets:
        if not isinstance(asset, dict) or not str(asset.get("output_path") or "").strip():
            raise ValueError("adaptive_blog asset manifest is invalid")
        expected_files.add(str(asset["output_path"]).replace("\\", "/"))

    actual_files = {path.relative_to(version_dir).as_posix() for path in files}
    unexpected = sorted(actual_files - expected_files)
    missing = sorted(expected_files - actual_files)
    if unexpected:
        raise ValueError(f"adaptive_blog version contains unexpected files: {unexpected}")
    if missing:
        raise ValueError(f"adaptive_blog version is missing required files: {missing}")

    renderer = _load_blog_renderer()
    renderer._validate_profile(blog)
    renderer._validation_ready(blog_path, blog)
    expected_markdown = renderer.render_markdown(blog, blog_path, version_dir)
    expected_html = renderer.render_html(blog, blog_path, version_dir)
    if (version_dir / "blog.md").read_text(encoding="utf-8") != expected_markdown:
        raise ValueError("rendered blog output does not match the validated source: blog.md")
    if (version_dir / "blog.html").read_text(encoding="utf-8") != expected_html:
        raise ValueError("rendered blog output does not match the validated source: blog.html")


def _validate_book_a4_publication(version_dir: Path, files: list[Path], vault_root: str) -> None:
    manuscript_path = version_dir / "manuscript.json"
    destination = _book_destination(vault_root)
    if not manuscript_path.is_file():
        if destination is not None:
            raise ValueError("book_a4 destination requires manuscript.json and a complete book package")
        return
    if destination is None:
        raise ValueError("book_a4 package must publish below 01 Manuscript/.../v0.N")

    manuscript = json.loads(manuscript_path.read_text(encoding="utf-8"))
    if not isinstance(manuscript, dict) or manuscript.get("output_profile") != "book_a4":
        raise ValueError("manuscript.json requires output_profile book_a4")
    source_markdown = str(manuscript.get("source_markdown") or "")
    if (
        not source_markdown
        or PurePosixPath(source_markdown).name != source_markdown
        or "\\" in source_markdown
        or PurePosixPath(source_markdown).suffix.lower() != ".md"
    ):
        raise ValueError("book_a4 source_markdown must name one version-root Markdown file")

    manifest_path = version_dir / "asset-manifest.json"
    validation_path = version_dir / "asset-validation.json"
    if not manifest_path.is_file() or not validation_path.is_file():
        raise ValueError("book_a4 asset manifest and validation report are required")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not isinstance(manifest.get("assets"), list):
        raise ValueError("book_a4 asset manifest is invalid")
    if not isinstance(validation, dict) or validation.get("status") != "ready":
        raise ValueError("book_a4 validation status must be ready before publication")

    current_inputs = {
        "manuscript_sha256": hashlib.sha256(manuscript_path.read_bytes()).hexdigest(),
        "asset_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    }
    if validation.get("validated_inputs") != current_inputs:
        raise ValueError("book_a4 validation is stale; validate the current package again")
    validated_outputs = validation.get("validated_outputs")
    if not isinstance(validated_outputs, dict):
        raise ValueError("book_a4 validation report is missing validated outputs")
    for output_name in ("manuscript.html", "manuscript.pdf"):
        output_path = version_dir / output_name
        actual_digest = hashlib.sha256(output_path.read_bytes()).hexdigest()
        if validated_outputs.get(output_name) != actual_digest:
            raise ValueError(f"book_a4 validated output does not match: {output_name}")

    if manuscript.get("template_version") in (2, 3):
        visual_entries = [manuscript.get("preview", {}).get("visual"), manuscript.get("practice_preparation", {}).get("visual")]
        visual_entries.extend(
            block.get("visual") for block in manuscript.get("practice_blocks", [])
            if isinstance(block, dict) and block.get("type") == "step"
        )
        if manuscript.get("real_world_use_visual"):
            visual_entries.append(manuscript.get("real_world_use_visual"))
    else:
        visual_entries = [manuscript.get("preview", {}).get("visual")]
        visual_entries.extend(step.get("visual") for step in manuscript.get("steps", []) if isinstance(step, dict))
        visual_entries.append(manuscript.get("real_world_use_visual"))
    visual_ids: set[str] = set()
    visual_paths: dict[str, str] = {}
    for visual in visual_entries:
        if not isinstance(visual, dict) or not str(visual.get("asset_id") or ""):
            raise ValueError("book_a4 visual metadata is incomplete")
        asset_id = str(visual["asset_id"])
        if asset_id in visual_ids:
            raise ValueError("book_a4 visual asset IDs must be unique")
        visual_ids.add(asset_id)
        visual_paths[asset_id] = _safe_asset_output_path(visual.get("image"), profile="book_a4")

    expected_files = {
        "production-plan.json",
        source_markdown,
        "manuscript.json",
        "asset-manifest.json",
        "asset-validation.json",
        "manuscript.html",
        "manuscript.pdf",
    }
    manifest_ids: set[str] = set()
    manifest_paths: set[str] = set()
    for asset in manifest["assets"]:
        if not isinstance(asset, dict) or not str(asset.get("asset_id") or ""):
            raise ValueError("book_a4 asset manifest is invalid")
        asset_id = str(asset["asset_id"])
        output_path = _safe_asset_output_path(asset.get("output_path"), profile="book_a4")
        if asset_id in manifest_ids or output_path in manifest_paths:
            raise ValueError("book_a4 asset IDs and output paths must be unique")
        manifest_ids.add(asset_id)
        manifest_paths.add(output_path)
        expected_files.add(output_path)
        if visual_paths.get(asset_id) != output_path:
            raise ValueError("book_a4 visual and manifest asset paths must match")
    if visual_ids != manifest_ids:
        raise ValueError("book_a4 visual and manifest asset sets must match exactly")

    actual_files = {path.relative_to(version_dir).as_posix() for path in files}
    unexpected = sorted(actual_files - expected_files)
    missing = sorted(expected_files - actual_files)
    if unexpected:
        raise ValueError(f"book_a4 version contains unexpected files: {unexpected}")
    if missing:
        raise ValueError(f"book_a4 version is missing required files: {missing}")

    fresh_validation = _load_book_validator().validate_package(manuscript, manifest, version_dir)
    if fresh_validation.get("status") != "ready":
        raise ValueError("book_a4 package is stale or invalid; validate it again")


def _failure_report(*, phase: str, published: list[dict], attempted_paths: list[str], error: Exception) -> dict:
    """Describe a failed, potentially partial publication without deleting remote data."""
    return {
        "status": "publication_failed",
        "phase": phase,
        "files": published,
        "error": str(error),
        "remote_state": "partial_publication_possible",
        "quarantine": {
            "status": "required",
            "automatic_cleanup": "disabled",
            "possibly_written_paths": attempted_paths,
            "retry_policy": "allocate_a_fresh_immutable_version",
        },
    }


def publish_version(config_path: Path, local_version_dir: Path, vault_relative_version_dir: str, base_url: str | None = None) -> dict:
    # This check must precede is_dir() and every report write. On Windows a
    # junction can otherwise redirect both validation and failure reports.
    _assert_safe_version_root(local_version_dir)
    if not local_version_dir.is_dir():
        raise ValueError("local_version_dir must be an existing directory")
    vault_root = _relative_path(vault_relative_version_dir)
    try:
        files = _version_files(local_version_dir)
        _validate_adaptive_blog_publication(local_version_dir, files, vault_root)
        _validate_book_a4_publication(local_version_dir, files, vault_root)
    except Exception as error:
        _write_report(local_version_dir, {
            "status": "publication_failed",
            "phase": "local_validation",
            "files": [],
            "error": str(error),
        })
        raise

    _assert_generic_destination(vault_root)

    # Capture the complete validated package before the first REST call.
    # Uploads below must use only these immutable byte snapshots.
    snapshots = [
        (path.relative_to(local_version_dir).as_posix(), path.read_bytes())
        for path in files
    ]
    published: list[dict] = []
    attempted_paths: list[str] = []
    try:
        existing = list_vault_directory(config_path, vault_root, base_url)
    except Exception as error:
        _write_report(local_version_dir, _failure_report(
            phase="preflight",
            published=[],
            attempted_paths=[],
            error=error,
        ))
        raise
    if existing is not None:
        # A collision is a safe preflight refusal, not a partial publication.
        # In particular, never replace a successful local publication report.
        raise ValueError("immutable version already exists in the Obsidian vault")
    try:
        for relative_path, content in snapshots:
            vault_path = str(PurePosixPath(vault_root) / relative_path)
            attempted_paths.append(vault_path)
            save_and_verify(config_path, vault_path, content, base_url)
            published.append({
                "local_path": relative_path,
                "vault_relative_path": vault_path,
                "sha256": hashlib.sha256(content).hexdigest(),
            })
    except Exception as error:
        _write_report(local_version_dir, _failure_report(
            phase="files",
            published=published,
            attempted_paths=attempted_paths,
            error=error,
        ))
        raise

    report = {"status": "published", "files": published}
    report_vault_path = str(PurePosixPath(vault_root) / REPORT_NAME)
    try:
        report_content = _report_bytes(report)
        attempted_paths.append(report_vault_path)
        save_and_verify(config_path, report_vault_path, report_content, base_url)
    except Exception as error:
        _write_report(local_version_dir, _failure_report(
            phase="publication_report",
            published=published,
            attempted_paths=attempted_paths,
            error=error,
        ))
        raise
    _write_report(local_version_dir, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--local-version-dir", required=True)
    parser.add_argument("--vault-relative-version-dir", required=True)
    parser.add_argument("--base-url")
    arguments = parser.parse_args()
    result = publish_version(
        Path(arguments.config),
        Path(arguments.local_version_dir),
        arguments.vault_relative_version_dir,
        arguments.base_url,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
