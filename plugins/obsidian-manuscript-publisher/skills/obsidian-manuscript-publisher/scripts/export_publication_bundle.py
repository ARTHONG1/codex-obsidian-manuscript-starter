#!/usr/bin/env python3
"""Export one verified manuscript version into a desktop publication bundle."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import html
import importlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tempfile
import unicodedata
from urllib.parse import quote
import uuid

validate_blog = None
validate_manuscript = None


VERSION_PATTERN = re.compile(r"^v0\.([1-9][0-9]*)$")
WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}
FORBIDDEN_COMPONENT = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
IMAGE_MARKDOWN = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
IMAGE_HTML = re.compile(r"(<img\b[^>]*?\bsrc=[\"'])([^\"']+)([\"'])", re.IGNORECASE)
MANAGED_GUIDE_HEADER = "[Codex Obsidian Manuscript - managed publication guide]"
MANAGED_INDEX_MARKER = "<!-- Codex Obsidian Manuscript - managed publication index -->"
STAGING_OWNER_MARKER = ".codex-publication-staging"
STAGING_OWNER_VALUE = "codex-obsidian-manuscript-publisher:v1"
EXPORT_MANIFEST = "_meta/export-manifest.json"
EXPORT_LOCK_NAME = ".codex-publication-export.lock"
INCOMPLETE_MARKER = ".codex-publication-incomplete.json"
OS_BENIGN_ROOT_FILES = frozenset({"desktop.ini", "Thumbs.db", ".DS_Store"})


class ExportError(ValueError):
    """A deterministic export failure with a stable machine-readable code."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def _acquire_export_lock(stream) -> None:
    stream.seek(0)
    stream.write(b"0")
    stream.flush()
    stream.seek(0)
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, BlockingIOError) as error:
        raise ExportError("export_locked", "another publication export is already running") from error


def _release_export_lock(stream) -> None:
    stream.seek(0)
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


@contextmanager
def _publication_lock(publication_root: Path):
    publication_root.mkdir(parents=True, exist_ok=True)
    stream = (publication_root / EXPORT_LOCK_NAME).open("a+b")
    acquired = False
    try:
        _acquire_export_lock(stream)
        acquired = True
        yield
    finally:
        if acquired:
            _release_export_lock(stream)
        stream.close()


def _load_runtime_dependencies() -> None:
    global validate_blog, validate_manuscript
    if validate_blog is None:
        validate_blog = importlib.import_module("validate_blog")
    if validate_manuscript is None:
        validate_manuscript = importlib.import_module("validate_manuscript")


@dataclass(frozen=True)
class ExportRequest:
    source_version_dir: Path
    publication_root: Path
    project_destination_root: str
    vault_path: Path | None = None


@dataclass(frozen=True)
class AssetExport:
    asset_id: str
    source_path: Path
    source_relative_path: str
    destination_relative_path: str
    insertion_label: str
    caption: str
    alt_text: str
    sha256: str


@dataclass(frozen=True)
class VerifiedPackage:
    profile: str
    source_version: str
    title: str
    item_parts: tuple[str, ...]
    source_dir: Path
    metadata: dict
    metadata_path: Path
    markdown_path: Path
    html_path: Path
    pdf_path: Path | None
    validation_path: Path
    assets: tuple[AssetExport, ...]
    source_hashes: dict[str, str]
    vault_publication_status: str
    project_destination_root: str


@dataclass(frozen=True)
class PromotionState:
    status: str
    latest: Path
    mode: str
    item_root: Path
    previous: Path | None = None
    history_destination: Path | None = None
    created_history: Path | None = None


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _load_json(path: Path, code: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ExportError(code, f"cannot read {path.name}: {error}") from error
    if not isinstance(value, dict):
        raise ExportError(code, f"{path.name} must contain a JSON object")
    return value


def _unsafe_link_reason(path: Path) -> str | None:
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(metadata.st_mode):
        return "symbolic link"
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if getattr(metadata, "st_file_attributes", 0) & reparse_flag:
        return "reparse point"
    return None


def _reject_reparse_tree(root: Path) -> None:
    reason = _unsafe_link_reason(root)
    if reason:
        raise ExportError("unsafe_path", f"source version must not be a {reason}")
    for path in root.rglob("*"):
        reason = _unsafe_link_reason(path)
        if reason:
            raise ExportError("unsafe_path", f"source package contains a {reason}: {path.name}")


def _reject_reparse_ancestors(path: Path) -> None:
    candidate = path
    while True:
        if candidate.exists():
            reason = _unsafe_link_reason(candidate)
            if reason:
                raise ExportError("unsafe_path", f"publication path contains a {reason}")
        if candidate.parent == candidate:
            return
        candidate = candidate.parent


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve())) == os.path.normcase(str(right.resolve()))


def _is_relative_to(candidate: Path, parent: Path) -> bool:
    try:
        candidate.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _safe_publication_boundary(request: ExportRequest) -> tuple[Path, Path]:
    raw_source = Path(os.path.abspath(os.fspath(request.source_version_dir)))
    raw_publication_root = Path(os.path.abspath(os.fspath(request.publication_root)))
    _reject_reparse_ancestors(raw_source)
    _reject_reparse_ancestors(raw_publication_root)
    source = raw_source.resolve()
    publication_root = raw_publication_root.resolve()
    if not source.is_dir():
        raise ExportError("unsafe_path", "source_version_dir must be an existing directory")
    anchor = Path(publication_root.anchor).resolve()
    if _same_path(publication_root, anchor) or _same_path(publication_root, Path.home()):
        raise ExportError("unsafe_path", "publication root cannot be a filesystem or user-profile root")
    if request.vault_path is not None:
        raw_vault = Path(os.path.abspath(os.fspath(request.vault_path)))
        _reject_reparse_ancestors(raw_vault)
        vault = raw_vault.resolve()
        if (
            _same_path(publication_root, vault)
            or _is_relative_to(publication_root, vault)
            or _is_relative_to(vault, publication_root)
        ):
            raise ExportError("unsafe_path", "publication root and Obsidian Vault must not overlap")
    if _same_path(publication_root, source) or _is_relative_to(publication_root, source) or _is_relative_to(source, publication_root):
        raise ExportError("unsafe_path", "source and publication paths must not overlap")
    _reject_reparse_tree(source)
    _reject_reparse_ancestors(publication_root)
    return source, publication_root


def _is_windows_reserved(value: str) -> bool:
    return value.split(".", 1)[0].upper() in WINDOWS_RESERVED


def _require_registry_component(raw: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ExportError("unsafe_path", "project destination root is required")
    value = unicodedata.normalize("NFC", raw)
    if value != value.strip() or value.endswith((".", " ")) or value in {".", ".."}:
        raise ExportError("unsafe_path", "project destination root is unsafe")
    if "/" in value or "\\" in value or FORBIDDEN_COMPONENT.search(value):
        raise ExportError("unsafe_path", "project destination root must be one folder name")
    if _is_windows_reserved(value):
        raise ExportError("unsafe_path", "project destination root is a Windows reserved name")
    return value


def sanitize_component(raw: object) -> str:
    normalized = unicodedata.normalize("NFC", str(raw or "")).strip()
    value = FORBIDDEN_COMPONENT.sub("_", normalized).rstrip(" .")
    changed = value != normalized
    if not value:
        value = "untitled"
        changed = True
    if _is_windows_reserved(value):
        value = f"_{value}"
        changed = True
    if len(value) > 120:
        changed = True
    if changed:
        suffix = "--" + _sha256_bytes(normalized.encode("utf-8"))[:8]
        value = value[: 120 - len(suffix)].rstrip(" .") + suffix
    return value[:120].rstrip(" .") or "untitled"


def _safe_asset_relative(value: object) -> str:
    raw = str(value or "")
    path = PurePosixPath(raw)
    parts = path.parts
    if (
        not raw
        or "\\" in raw
        or path.is_absolute()
        or not parts
        or parts[0] != "assets"
        or any(part in {"", ".", ".."} for part in parts)
        or re.match(r"^[A-Za-z]:", raw)
        or raw.startswith("//")
    ):
        raise ExportError("unsafe_path", "asset path must remain below version-local assets")
    return path.as_posix()


def _version_number(name: str) -> int:
    match = VERSION_PATTERN.fullmatch(name)
    if not match:
        raise ExportError("unsafe_path", "source folder must be an immutable v0.N version")
    return int(match.group(1))


def _publication_status(source: Path) -> str:
    report_path = source / "publication-validation.json"
    if not report_path.is_file():
        return "not_published"
    report = _load_json(report_path, "publication_report_invalid")
    status = str(report.get("status") or "unknown")
    return status if status in {"published", "publication_failed"} else "unknown"


def _assert_exact_allowlist(source: Path, expected: set[str]) -> None:
    actual = {
        path.relative_to(source).as_posix()
        for path in source.rglob("*")
        if path.is_file() and path.relative_to(source).as_posix() != "publication-validation.json"
    }
    unexpected = sorted(actual - expected)
    missing = sorted(expected - actual)
    if unexpected:
        raise ExportError("unexpected_source_file", f"source contains unlisted files: {unexpected}")
    if missing:
        raise ExportError("missing_source_file", f"source is missing required files: {missing}")


def _manifest_assets(source: Path, manifest: dict) -> dict[str, dict]:
    records = manifest.get("assets")
    if not isinstance(records, list):
        raise ExportError("manifest_invalid", "asset-manifest.json requires an assets list")
    if not records:
        raise ExportError("manifest_invalid", "asset-manifest.json requires at least one asset")
    result: dict[str, dict] = {}
    seen_paths: set[str] = set()
    for record in records:
        if not isinstance(record, dict) or not str(record.get("asset_id") or ""):
            raise ExportError("manifest_invalid", "each asset requires asset_id")
        asset_id = str(record["asset_id"])
        relative = _safe_asset_relative(record.get("output_path"))
        if asset_id in result or relative in seen_paths:
            raise ExportError("manifest_invalid", "asset IDs and output paths must be unique")
        path = source / Path(*PurePosixPath(relative).parts)
        if not path.is_file():
            raise ExportError("missing_source_file", f"manifest asset is missing: {relative}")
        actual_hash = _sha256_file(path)
        if actual_hash != str(record.get("sha256") or ""):
            raise ExportError("asset_hash_mismatch", f"asset hash differs: {relative}")
        result[asset_id] = record
        seen_paths.add(relative)
    return result


def _require_validated_outputs(validation: dict, source: Path, relative_paths: tuple[str, ...]) -> None:
    expected: dict[str, str] = {}
    for relative in relative_paths:
        path = source / relative
        if not path.is_file():
            raise ExportError("missing_source_file", f"rendered output is missing: {relative}")
        expected[relative] = _sha256_file(path)
    if validation.get("validated_outputs") != expected:
        raise ExportError("stale_rendered_output", "rendered outputs differ from the validated render hashes")


def _asset_export(
    source: Path,
    visual: dict,
    record: dict,
    sequence: int,
    filename_label: str,
    insertion_label: str,
) -> AssetExport:
    asset_id = str(visual.get("asset_id") or "")
    source_relative = _safe_asset_relative(record.get("output_path"))
    if _safe_asset_relative(visual.get("image")) != source_relative:
        raise ExportError("manifest_invalid", f"visual and manifest paths differ for {asset_id}")
    suffix = Path(source_relative).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg"}:
        raise ExportError("manifest_invalid", "publication assets must be PNG or JPEG")
    destination_name = f"{sequence:02d}-{sanitize_component(filename_label)}{suffix}"
    return AssetExport(
        asset_id=asset_id,
        source_path=source / Path(*PurePosixPath(source_relative).parts),
        source_relative_path=source_relative,
        destination_relative_path=f"images/{destination_name}",
        insertion_label=insertion_label,
        caption=str(visual.get("caption") or "").strip(),
        alt_text=str(visual.get("alt_text") or insertion_label).strip(),
        sha256=str(record["sha256"]),
    )


def _inspect_book(request: ExportRequest, source: Path, project: str) -> VerifiedPackage:
    metadata_path = source / "manuscript.json"
    manifest_path = source / "asset-manifest.json"
    validation_path = source / "asset-validation.json"
    metadata = _load_json(metadata_path, "metadata_invalid")
    manifest = _load_json(manifest_path, "manifest_invalid")
    validation = _load_json(validation_path, "validation_not_ready")
    if metadata.get("output_profile") != "book_a4" or validation.get("status") != "ready":
        raise ExportError("validation_not_ready", "book_a4 package must have ready validation")
    current_inputs = {
        "manuscript_sha256": _sha256_file(metadata_path),
        "asset_manifest_sha256": _sha256_file(manifest_path),
    }
    if validation.get("validated_inputs") != current_inputs:
        raise ExportError("stale_validation", "book_a4 validation inputs changed")
    records = _manifest_assets(source, manifest)
    fresh = validate_manuscript.validate_package(metadata, manifest, source)
    if fresh.get("status") != "ready":
        raise ExportError("validation_not_ready", "book_a4 package no longer validates")
    source_markdown = str(metadata.get("source_markdown") or "")
    if not source_markdown or PurePosixPath(source_markdown).name != source_markdown or Path(source_markdown).suffix.lower() != ".md":
        raise ExportError("unsafe_path", "source_markdown must be one version-root Markdown file")
    markdown_path = source / source_markdown
    html_path = source / "manuscript.html"
    pdf_path = source / "manuscript.pdf"
    _require_validated_outputs(
        validation,
        source,
        (source_markdown, "manuscript.html", "manuscript.pdf"),
    )
    visuals: list[tuple[str, str, dict]] = [
        ("미리보기", "미리보기", metadata.get("preview", {}).get("visual")),
    ]
    if metadata.get("template_version") in (2, 3):
        visuals.append(("preparation", "실습 사전 준비", metadata.get("practice_preparation", {}).get("visual")))
        for block in metadata.get("practice_blocks", []):
            if isinstance(block, dict) and block.get("type") == "step":
                index = int(block.get("number", 0))
                visuals.append((f"Step-{index:02d}", str(block.get("title") or f"Step {index}"), block.get("visual")))
    for index, step in enumerate(metadata.get("steps", []), 1):
        visuals.append((f"Step-{index:02d}", str(step.get("title") or f"Step {index}"), step.get("visual")))
    visuals.append(("실전-활용", "실전 활용하기", metadata.get("real_world_use_visual")))
    if metadata.get("template_version") in (2, 3) and not metadata.get("real_world_use_visual"):
        visuals.pop()
    assets: list[AssetExport] = []
    used: set[str] = set()
    for sequence, (filename, insertion, visual) in enumerate(visuals, 1):
        if not isinstance(visual, dict):
            raise ExportError("manifest_invalid", "book visual metadata is incomplete")
        asset_id = str(visual.get("asset_id") or "")
        if asset_id not in records or asset_id in used:
            raise ExportError("manifest_invalid", "book visual asset mapping is incomplete")
        used.add(asset_id)
        assets.append(_asset_export(source, visual, records[asset_id], sequence, filename, insertion))
    if used != set(records):
        raise ExportError("manifest_invalid", "book manifest contains unused assets")
    expected = {
        "production-plan.json", source_markdown, "manuscript.json", "asset-manifest.json",
        "asset-validation.json", "manuscript.html", "manuscript.pdf",
        *(asset.source_relative_path for asset in assets),
    }
    _assert_exact_allowlist(source, expected)
    if not all(path.is_file() for path in (markdown_path, html_path, pdf_path)):
        raise ExportError("missing_source_file", "book render outputs are incomplete")
    chapter = sanitize_component(metadata.get("chapter"))
    title = str(metadata.get("title") or "원고")
    chapter_folder = sanitize_component(f"{chapter} {title}")
    return VerifiedPackage(
        profile="book_a4",
        source_version=source.name,
        title=title,
        item_parts=(project, "01 출판 원고형", sanitize_component(metadata.get("part")), chapter_folder),
        source_dir=source,
        metadata=metadata,
        metadata_path=metadata_path,
        markdown_path=markdown_path,
        html_path=html_path,
        pdf_path=pdf_path,
        validation_path=validation_path,
        assets=tuple(assets),
        source_hashes={relative: _sha256_file(source / Path(*PurePosixPath(relative).parts)) for relative in sorted(expected)},
        vault_publication_status=_publication_status(source),
        project_destination_root=project,
    )


def _inspect_blog(request: ExportRequest, source: Path, project: str) -> VerifiedPackage:
    metadata_path = source / "blog.json"
    manifest_path = source / "asset-manifest.json"
    validation_path = source / "blog-validation.json"
    metadata = _load_json(metadata_path, "metadata_invalid")
    manifest = _load_json(manifest_path, "manifest_invalid")
    validation = _load_json(validation_path, "validation_not_ready")
    if metadata.get("output_profile") != "adaptive_blog" or validation.get("status") != "ready":
        raise ExportError("validation_not_ready", "adaptive_blog package must have ready validation")
    current_inputs = {
        "blog_sha256": _sha256_file(metadata_path),
        "asset_manifest_sha256": _sha256_file(manifest_path),
    }
    if validation.get("validated_inputs") != current_inputs:
        raise ExportError("stale_validation", "adaptive_blog validation inputs changed")
    records = _manifest_assets(source, manifest)
    fresh = validate_blog.validate_package(metadata, manifest, source)
    if fresh.get("status") != "ready":
        raise ExportError("validation_not_ready", "adaptive_blog package no longer validates")
    visuals: list[tuple[str, str, dict]] = [("대표이미지", "대표이미지", metadata.get("hero_visual"))]
    visual_number = 0
    for section in metadata.get("sections", []):
        if section.get("visual") is not None:
            visual_number += 1
            visuals.append((f"검증근거-{visual_number}", str(section.get("heading") or "본문 이미지"), section["visual"]))
    assets: list[AssetExport] = []
    used: set[str] = set()
    for sequence, (filename, insertion, visual) in enumerate(visuals, 1):
        if not isinstance(visual, dict):
            raise ExportError("manifest_invalid", "blog visual metadata is incomplete")
        asset_id = str(visual.get("asset_id") or "")
        if asset_id not in records or asset_id in used:
            raise ExportError("manifest_invalid", "blog visual asset mapping is incomplete")
        used.add(asset_id)
        assets.append(_asset_export(source, visual, records[asset_id], sequence, filename, insertion))
    if used != set(records):
        raise ExportError("manifest_invalid", "blog manifest contains unused assets")
    expected = {
        "blog.json", "asset-manifest.json", "blog-validation.json", "blog.md", "blog.html",
        *(asset.source_relative_path for asset in assets),
    }
    _assert_exact_allowlist(source, expected)
    markdown_path = source / "blog.md"
    html_path = source / "blog.html"
    if not markdown_path.is_file() or not html_path.is_file():
        raise ExportError("missing_source_file", "blog render outputs are incomplete")
    _require_validated_outputs(validation, source, ("blog.md", "blog.html"))
    slug = str(metadata.get("slug") or "")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) or _is_windows_reserved(slug):
        raise ExportError("unsafe_path", "blog slug is unsafe")
    return VerifiedPackage(
        profile="adaptive_blog",
        source_version=source.name,
        title=str(metadata.get("title") or slug),
        item_parts=(project, "02 범용 블로그형", slug),
        source_dir=source,
        metadata=metadata,
        metadata_path=metadata_path,
        markdown_path=markdown_path,
        html_path=html_path,
        pdf_path=None,
        validation_path=validation_path,
        assets=tuple(assets),
        source_hashes={relative: _sha256_file(source / Path(*PurePosixPath(relative).parts)) for relative in sorted(expected)},
        vault_publication_status=_publication_status(source),
        project_destination_root=project,
    )


def inspect_verified_package(request: ExportRequest) -> VerifiedPackage:
    source, _ = _safe_publication_boundary(request)
    _version_number(source.name)
    project = _require_registry_component(request.project_destination_root)
    has_book = (source / "manuscript.json").is_file()
    has_blog = (source / "blog.json").is_file()
    if has_book == has_blog:
        raise ExportError("profile_ambiguous", "exactly one profile metadata file is required")
    return _inspect_book(request, source, project) if has_book else _inspect_blog(request, source, project)


def _image_marker(sequence: int, label: str, caption: str) -> str:
    return f"[이미지 {sequence:02d} 삽입: {label}]\n캡션: {caption}"


def _book_copy_text(package: VerifiedPackage) -> str:
    data = package.metadata
    assets = iter(package.assets)
    preview_asset = next(assets)
    lines = [
        f"[{data['part']} - {data['chapter']}] {data['title']}", "",
        "[이번 챕터에서는]", str(data["chapter_intro"]), "",
        "[한눈에 보기]",
    ]
    lines.extend(f"{key}: {value}" for key, value in data["quick_reference"].items())
    preview = data["preview"]
    lines.extend([
        "", "[미리 보기]", str(preview.get("result_title") or ""),
        str(preview.get("result_summary") or ""),
        _image_marker(1, preview_asset.insertion_label, preview_asset.caption),
        "", "[실습하기]",
    ])
    if data.get("template_version") in (2, 3):
        preparation_asset = next(assets)
        preparation = data["practice_preparation"]
        lines.extend(["", "[실습 사전 준비]", str(preparation.get("body") or ""), _image_marker(2, preparation_asset.insertion_label, preparation_asset.caption), ""])
        sequence = 3
        for block in data["practice_blocks"]:
            if block.get("type") == "step":
                asset = next(assets)
                body = " ".join(str(sentence).strip() for sentence in block.get("body", []))
                lines.extend([f"Step {block['number']}. {block['title']}", body, _image_marker(sequence, asset.insertion_label, asset.caption), ""])
                sequence += 1
            else:
                lines.extend(["[꿀팁 더하기]", " ".join(str(sentence).strip() for sentence in block.get("body", [])), ""])
        lines.extend(["[실전 활용하기]", str(data["real_world_use"]), "", f"※ {data['verification_note']}"])
        return "\n".join(lines).rstrip() + "\n"
    for index, step in enumerate(data["steps"], 1):
        asset = next(assets)
        interaction = step["interaction"]
        body = " ".join(str(interaction[field]).strip() for field in ("user_request", "codex_action", "user_check"))
        lines.extend([
            f"Step {index}. {step['title']}", body,
            _image_marker(index + 1, asset.insertion_label, asset.caption), "",
        ])
    final_asset = next(assets)
    lines.extend([
        "[실전 활용하기]", str(data["real_world_use"]),
        _image_marker(len(package.assets), final_asset.insertion_label, final_asset.caption), "",
        "[꿀팁 더하기]", str(data["tip"]), "",
        f"※ {data['verification_note']}",
    ])
    return "\n".join(lines).rstrip() + "\n"


def _blog_copy_text(package: VerifiedPackage) -> str:
    data = package.metadata
    assets_by_id = {asset.asset_id: (index, asset) for index, asset in enumerate(package.assets, 1)}
    hero_index, hero = assets_by_id[str(data["hero_visual"]["asset_id"])]
    lines = [
        str(data["title"]), str(data["dek"]), "",
        _image_marker(hero_index, hero.insertion_label, hero.caption), "",
        str(data["lead"]), "",
    ]
    for section in data["sections"]:
        lines.append(str(section["heading"]))
        lines.extend(str(paragraph) for paragraph in section["paragraphs"])
        visual = section.get("visual")
        if visual is not None:
            sequence, asset = assets_by_id[str(visual["asset_id"])]
            lines.append(_image_marker(sequence, asset.insertion_label, asset.caption))
        lines.append("")
    lines.extend([
        "지금 적용해 볼 일", str(data["next_action"]), "",
        str(data["closing"]), "",
        " ".join(f"#{str(tag).replace(' ', '_')}" for tag in data["tags"]),
    ])
    return "\n".join(lines).rstrip() + "\n"


def _rewrite_markdown(source: str, assets: tuple[AssetExport, ...]) -> str:
    rewritten = source
    allowed_destinations = {asset.destination_relative_path for asset in assets}
    for asset in assets:
        rewritten = rewritten.replace(asset.source_relative_path, asset.destination_relative_path)
        rewritten = rewritten.replace(f"./{asset.source_relative_path}", asset.destination_relative_path)
    for match in IMAGE_MARKDOWN.finditer(rewritten):
        target = match.group(1).split(" ", 1)[0].strip("<>")
        if target not in allowed_destinations:
            raise ExportError("unexpected_source_file", f"Markdown references an unlisted image: {target}")
    return rewritten


def _rewrite_html(source: str, package: VerifiedPackage) -> str:
    rewritten = source
    destinations = {asset.destination_relative_path for asset in package.assets}
    for asset in package.assets:
        candidates = {
            asset.source_relative_path,
            f"./{asset.source_relative_path}",
            asset.source_path.resolve().as_uri(),
        }
        for candidate in sorted(candidates, key=len, reverse=True):
            rewritten = rewritten.replace(candidate, asset.destination_relative_path)
    for match in IMAGE_HTML.finditer(rewritten):
        if match.group(2) not in destinations:
            raise ExportError("unexpected_source_file", f"HTML references an unlisted image: {match.group(2)}")
    return rewritten


def _insertion_guide(package: VerifiedPackage) -> str:
    rows = [
        "# 이미지 삽입 순서", "",
        "| 순서 | 파일명 | 삽입 위치 | 캡션 | 대체 텍스트 | asset_id | 원본 파일 | SHA-256 |",
        "| ---: | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for index, asset in enumerate(package.assets, 1):
        values = (
            str(index), Path(asset.destination_relative_path).name, asset.insertion_label,
            asset.caption, asset.alt_text, asset.asset_id, asset.source_relative_path, asset.sha256,
        )
        escaped = [value.replace("|", "\\|").replace("\n", " ") for value in values]
        rows.append("| " + " | ".join(escaped) + " |")
    return "\n".join(rows) + "\n"


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _content_fingerprint(package: VerifiedPackage, exported_files: dict[str, str], image_map: list[dict]) -> str:
    payload = {
        "profile": package.profile,
        "project_destination_root": package.project_destination_root,
        "source_version": package.source_version,
        "source_hashes": package.source_hashes,
        "exported_files": exported_files,
        "image_rename_map": image_map,
    }
    return _sha256_bytes(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _manifest_content_fingerprint(manifest: dict) -> str:
    payload = {
        "profile": manifest.get("output_profile"),
        "project_destination_root": manifest.get("project_destination_root"),
        "source_version": manifest.get("source_version"),
        "source_hashes": manifest.get("source_hashes"),
        "exported_files": manifest.get("exported_files"),
        "image_rename_map": manifest.get("image_rename_map"),
    }
    return _sha256_bytes(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _snapshot_source_files(package: VerifiedPackage) -> dict[str, bytes]:
    expected = set(package.source_hashes)
    _assert_exact_allowlist(package.source_dir, expected)
    snapshots: dict[str, bytes] = {}
    for relative, expected_hash in package.source_hashes.items():
        path = package.source_dir / Path(*PurePosixPath(relative).parts)
        try:
            content = path.read_bytes()
        except OSError as error:
            raise ExportError("source_changed", f"source file became unreadable: {relative}") from error
        if _sha256_bytes(content) != expected_hash:
            raise ExportError("source_changed", f"source file changed after inspection: {relative}")
        snapshots[relative] = content
    return snapshots


def build_bundle(package: VerifiedPackage, staging_dir: Path) -> dict:
    if staging_dir.exists():
        raise ExportError("unsafe_path", "staging directory must not already exist")
    source_snapshots = _snapshot_source_files(package)
    staging_dir.mkdir(parents=False)
    _atomic_write(staging_dir / STAGING_OWNER_MARKER, STAGING_OWNER_VALUE.encode("utf-8"))
    text_name = "01 본문-복사용.txt"
    markdown_name = "02 원고.md" if package.profile == "book_a4" else "02 블로그.md"
    guide_name = "05 이미지-삽입순서.md" if package.profile == "book_a4" else "04 이미지-삽입순서.md"
    copy_text = _book_copy_text(package) if package.profile == "book_a4" else _blog_copy_text(package)
    _atomic_write(staging_dir / text_name, copy_text.encode("utf-8"))
    _atomic_write(
        staging_dir / markdown_name,
        _rewrite_markdown(
            source_snapshots[package.markdown_path.relative_to(package.source_dir).as_posix()].decode("utf-8"),
            package.assets,
        ).encode("utf-8"),
    )
    _atomic_write(
        staging_dir / "03 미리보기.html",
        _rewrite_html(
            source_snapshots[package.html_path.relative_to(package.source_dir).as_posix()].decode("utf-8"),
            package,
        ).encode("utf-8"),
    )
    if package.pdf_path is not None:
        _atomic_write(
            staging_dir / "04 인쇄용.pdf",
            source_snapshots[package.pdf_path.relative_to(package.source_dir).as_posix()],
        )
    _atomic_write(staging_dir / guide_name, _insertion_guide(package).encode("utf-8"))
    image_map = []
    for asset in package.assets:
        _atomic_write(
            staging_dir / Path(*PurePosixPath(asset.destination_relative_path).parts),
            source_snapshots[asset.source_relative_path],
        )
        image_map.append({
            "asset_id": asset.asset_id,
            "source_relative_path": asset.source_relative_path,
            "exported_relative_path": asset.destination_relative_path,
            "sha256": asset.sha256,
        })
    exported_files = {
        path.relative_to(staging_dir).as_posix(): _sha256_file(path)
        for path in sorted(staging_dir.rglob("*"))
        if path.is_file() and path.name != STAGING_OWNER_MARKER
    }
    manifest = {
        "schema_version": 1,
        "output_profile": package.profile,
        "project_destination_root": package.project_destination_root,
        "title": package.title,
        "source_version": package.source_version,
        "source_hashes": package.source_hashes,
        "validation_status": "ready",
        "vault_publication_status": package.vault_publication_status,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "exported_files": exported_files,
        "image_rename_map": image_map,
    }
    manifest["content_fingerprint"] = _content_fingerprint(package, exported_files, image_map)
    _atomic_write(
        staging_dir / Path(*PurePosixPath(EXPORT_MANIFEST).parts),
        (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )
    verify_bundle(staging_dir, allow_owner_marker=True)
    (staging_dir / STAGING_OWNER_MARKER).unlink()
    verify_bundle(staging_dir)
    return manifest


def verify_bundle(bundle_dir: Path, *, allow_owner_marker: bool = False) -> dict:
    _reject_reparse_tree(bundle_dir)
    manifest_path = bundle_dir / Path(*PurePosixPath(EXPORT_MANIFEST).parts)
    manifest = _load_json(manifest_path, "bundle_invalid")
    exported = manifest.get("exported_files")
    if not isinstance(exported, dict):
        raise ExportError("bundle_invalid", "export manifest is missing file hashes")
    actual = {
        path.relative_to(bundle_dir).as_posix()
        for path in bundle_dir.rglob("*")
        if path.is_file()
    }
    if allow_owner_marker and STAGING_OWNER_MARKER in actual:
        marker = bundle_dir / STAGING_OWNER_MARKER
        if marker.read_text(encoding="utf-8") != STAGING_OWNER_VALUE:
            raise ExportError("bundle_invalid", "staging ownership marker is invalid")
        actual.remove(STAGING_OWNER_MARKER)
    expected = set(exported) | {EXPORT_MANIFEST}
    if actual != expected:
        raise ExportError("bundle_invalid", "bundle files differ from export manifest")
    for relative, digest in exported.items():
        path = bundle_dir / Path(*PurePosixPath(relative).parts)
        if _sha256_file(path) != digest:
            raise ExportError("bundle_invalid", f"exported file hash differs: {relative}")
    if manifest.get("content_fingerprint") != _manifest_content_fingerprint(manifest):
        raise ExportError("bundle_invalid", "export manifest fingerprint is invalid")
    return manifest


def _same_export(existing_dir: Path, new_manifest: dict) -> bool:
    try:
        existing = verify_bundle(existing_dir)
    except ExportError as error:
        raise ExportError("immutable_export_conflict", str(error)) from error
    return existing.get("content_fingerprint") == new_manifest.get("content_fingerprint")


def _safe_remove_owned(path: Path, item_root: Path) -> None:
    resolved = path.resolve()
    if resolved.parent != item_root.resolve() or not path.name.startswith((".staging-", ".previous-")):
        raise ExportError("unsafe_path", "refusing to remove a non-owned directory")
    reason = _unsafe_link_reason(path)
    if reason:
        raise ExportError("unsafe_path", f"refusing to remove an owned path that is a {reason}")
    if path.exists():
        _reject_reparse_tree(path)
        if path.name.startswith(".staging-"):
            marker = path / STAGING_OWNER_MARKER
            marker_owned = marker.is_file() and marker.read_text(encoding="utf-8") == STAGING_OWNER_VALUE
            if not marker_owned:
                try:
                    verify_bundle(path)
                except ExportError as error:
                    raise ExportError("recovery_invalid", "staging directory is not exporter-owned") from error
        else:
            try:
                verify_bundle(path)
            except ExportError as error:
                raise ExportError("recovery_invalid", "previous directory is not a verified bundle") from error
        shutil.rmtree(path)


def _item_root(publication_root: Path, package: VerifiedPackage) -> Path:
    candidate = publication_root.joinpath(*package.item_parts)
    if not _is_relative_to(candidate, publication_root):
        raise ExportError("unsafe_path", "publication item escapes the selected root")
    _reject_reparse_ancestors(candidate)
    return candidate


def _verified_owned_bundles(item_root: Path, prefix: str) -> list[tuple[Path, dict]]:
    bundles: list[tuple[Path, dict]] = []
    if not item_root.is_dir():
        return bundles
    for path in sorted(item_root.iterdir(), key=lambda candidate: candidate.name):
        if not path.name.startswith(prefix):
            continue
        if _unsafe_link_reason(path) or not path.is_dir() or path.resolve().parent != item_root.resolve():
            raise ExportError("recovery_invalid", f"interrupted export path is unsafe: {path.name}")
        if prefix == ".staging-":
            marker = path / STAGING_OWNER_MARKER
            if marker.is_file() and marker.read_text(encoding="utf-8") == STAGING_OWNER_VALUE:
                _reject_reparse_tree(path)
                bundles.append((path, {}))
                continue
        try:
            bundles.append((path, verify_bundle(path)))
        except ExportError as error:
            raise ExportError("recovery_invalid", f"interrupted export bundle is not verified: {path.name}") from error
    return bundles


def recover_item_root(item_root: Path) -> None:
    """Recover only verified exporter-owned interruption artifacts in one exact item root."""

    if not item_root.exists():
        return
    _reject_reparse_ancestors(item_root)
    previous_bundles = _verified_owned_bundles(item_root, ".previous-")
    staging_bundles = _verified_owned_bundles(item_root, ".staging-")
    if len(previous_bundles) > 1:
        raise ExportError("recovery_ambiguous", "multiple verified previous bundles require manual review")

    latest = item_root / "00 최신본"
    latest_manifest = None
    if latest.exists():
        try:
            latest_manifest = verify_bundle(latest)
        except ExportError as error:
            raise ExportError(
                "immutable_export_conflict",
                "the existing latest bundle is damaged or unverified",
            ) from error
    if previous_bundles:
        previous, previous_manifest = previous_bundles[0]
        if latest_manifest is None:
            os.replace(previous, latest)
            latest_manifest = previous_manifest
        else:
            previous_version = str(previous_manifest.get("source_version") or "")
            _version_number(previous_version)
            history_root = item_root / "99 이전버전"
            _reject_reparse_ancestors(history_root)
            history_root.mkdir(exist_ok=True)
            destination = history_root / previous_version
            if destination.exists():
                if not _same_export(destination, previous_manifest):
                    raise ExportError("immutable_export_conflict", "interrupted previous bundle conflicts with history")
                _safe_remove_owned(previous, item_root)
            else:
                os.replace(previous, destination)

    for staging, _ in staging_bundles:
        _safe_remove_owned(staging, item_root)


def _promote(package: VerifiedPackage, publication_root: Path, item_root: Path, staging: Path, manifest: dict) -> PromotionState:
    latest = item_root / "00 최신본"
    history_root = item_root / "99 이전버전"
    selected_number = _version_number(package.source_version)
    if not latest.exists():
        os.replace(staging, latest)
        return PromotionState("exported", latest, "created_latest", item_root)
    try:
        latest_manifest = verify_bundle(latest)
    except ExportError as error:
        _safe_remove_owned(staging, item_root)
        raise ExportError("immutable_export_conflict", "the existing latest bundle is damaged or unverified") from error
    latest_version = str(latest_manifest.get("source_version") or "")
    latest_number = _version_number(latest_version)
    if selected_number == latest_number:
        if _same_export(latest, manifest):
            _safe_remove_owned(staging, item_root)
            return PromotionState("already_exported", latest, "unchanged", item_root)
        _safe_remove_owned(staging, item_root)
        raise ExportError("immutable_export_conflict", "the same immutable version already has different bytes")
    if selected_number < latest_number:
        _reject_reparse_ancestors(history_root)
        history_root.mkdir(exist_ok=True)
        destination = history_root / package.source_version
        if destination.exists():
            if _same_export(destination, manifest):
                _safe_remove_owned(staging, item_root)
                return PromotionState("already_exported", latest, "unchanged", item_root)
            _safe_remove_owned(staging, item_root)
            raise ExportError("immutable_export_conflict", "history already contains different bytes for this version")
        os.replace(staging, destination)
        return PromotionState(
            "history_exported",
            latest,
            "created_history",
            item_root,
            created_history=destination,
        )
    _reject_reparse_ancestors(history_root)
    history_root.mkdir(exist_ok=True)
    history_destination = history_root / latest_version
    if history_destination.exists() and not _same_export(history_destination, latest_manifest):
        _safe_remove_owned(staging, item_root)
        raise ExportError("immutable_export_conflict", "previous latest conflicts with immutable history")
    previous = item_root / f".previous-{uuid.uuid4().hex}"
    os.replace(latest, previous)
    try:
        os.replace(staging, latest)
    except Exception as error:
        os.replace(previous, latest)
        raise
    return PromotionState(
        "exported",
        latest,
        "replaced_latest",
        item_root,
        previous=previous,
        history_destination=history_destination,
    )


def _remove_verified_bundle_as_owned(bundle: Path, item_root: Path) -> None:
    temporary = item_root / f".staging-rollback-{uuid.uuid4().hex}"
    os.replace(bundle, temporary)
    verify_bundle(temporary)
    _safe_remove_owned(temporary, item_root)


def _rollback_promotion(state: PromotionState) -> None:
    if state.mode == "unchanged":
        return
    if state.mode == "created_latest":
        if state.latest.exists():
            _remove_verified_bundle_as_owned(state.latest, state.item_root)
        return
    if state.mode == "created_history":
        if state.created_history and state.created_history.exists():
            _remove_verified_bundle_as_owned(state.created_history, state.item_root)
        return
    if state.mode != "replaced_latest" or state.previous is None:
        raise ExportError("rollback_failed", "unknown publication promotion state")

    if state.latest.exists():
        _remove_verified_bundle_as_owned(state.latest, state.item_root)
    if state.previous.exists():
        os.replace(state.previous, state.latest)
        return
    if state.history_destination and state.history_destination.exists():
        shutil.copytree(state.history_destination, state.latest)
        verify_bundle(state.latest)
        return
    raise ExportError("rollback_failed", "the previous verified latest could not be restored")


def _commit_promotion(state: PromotionState) -> None:
    if state.mode != "replaced_latest":
        return
    if state.previous is None or state.history_destination is None or not state.previous.exists():
        raise ExportError("recovery_invalid", "pending previous bundle is missing")
    if state.history_destination.exists():
        previous_manifest = verify_bundle(state.previous)
        if not _same_export(state.history_destination, previous_manifest):
            raise ExportError("immutable_export_conflict", "previous latest conflicts with immutable history")
        _safe_remove_owned(state.previous, state.item_root)
    else:
        os.replace(state.previous, state.history_destination)


def _usage_content() -> str:
    return (
        f"{MANAGED_GUIDE_HEADER}\n"
        "1. 각 원고의 00 최신본에서 01 본문-복사용.txt를 열어 글을 복사합니다.\n"
        "2. 이미지-삽입순서.md를 보며 images 폴더의 번호순 이미지를 업로드합니다.\n"
        "3. 03 미리보기.html과 책 원고의 04 인쇄용.pdf는 화면·인쇄 확인에 사용합니다.\n"
        "옵시디언 보관함은 원본 기록이며, 바탕화면 출판함은 검증된 복사용 결과입니다.\n"
    )


def _write_usage(publication_root: Path) -> None:
    destination = publication_root / "00 사용 방법.txt"
    if destination.exists():
        current = destination.read_text(encoding="utf-8-sig")
        if not current.startswith(MANAGED_GUIDE_HEADER):
            raise ExportError("unmanaged_root_file", "refusing to overwrite an unmanaged usage file")
    _atomic_write(destination, _usage_content().encode("utf-8"))


def _preflight_root_files(publication_root: Path) -> None:
    if not publication_root.exists():
        return
    managed_files = (
        (publication_root / "00 사용 방법.txt", MANAGED_GUIDE_HEADER),
        (publication_root / "00 원고 목록.html", MANAGED_INDEX_MARKER),
    )
    for managed_path, marker in managed_files:
        if not managed_path.exists():
            continue
        try:
            current = managed_path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as error:
            raise ExportError("unmanaged_root_file", "cannot verify an existing managed root file") from error
        if not current.startswith(marker):
            raise ExportError("unmanaged_root_file", "refusing to overwrite an unmanaged root file")
    managed_names = {path.name for path, _ in managed_files}
    managed_names.update({EXPORT_LOCK_NAME, INCOMPLETE_MARKER})
    unexpected = sorted(
        path.name
        for path in publication_root.iterdir()
        if path.is_file()
        and path.name not in managed_names
        and path.name not in OS_BENIGN_ROOT_FILES
    )
    if unexpected:
        raise ExportError(
            "unexpected_root_file",
            f"publication root contains an unrecognized file: {unexpected[0]}",
        )


def _snapshot_root_file(path: Path) -> bytes | None:
    return path.read_bytes() if path.is_file() else None


def _restore_root_file(path: Path, snapshot: bytes | None) -> None:
    if snapshot is None:
        if path.exists():
            path.unlink()
        return
    _atomic_write(path, snapshot)


def regenerate_root_index(publication_root: Path) -> Path:
    root = publication_root.resolve()
    entries = []
    for manifest_path in root.glob("**/00 최신본/_meta/export-manifest.json"):
        if any(_unsafe_link_reason(parent) for parent in [manifest_path, *manifest_path.parents] if _is_relative_to(parent, root)):
            continue
        latest = manifest_path.parents[1]
        try:
            manifest = verify_bundle(latest)
        except ExportError:
            continue
        relative_latest = latest.relative_to(root)
        profile = str(manifest["output_profile"])
        copy_link = quote((relative_latest / "01 본문-복사용.txt").as_posix(), safe="/")
        preview_link = quote((relative_latest / "03 미리보기.html").as_posix(), safe="/")
        pdf_link = ""
        if profile == "book_a4":
            pdf_link = f' · <a href="{quote((relative_latest / "04 인쇄용.pdf").as_posix(), safe="/")}">PDF</a>'
        entries.append({
            "project": relative_latest.parts[0],
            "profile": "출판 원고형" if profile == "book_a4" else "범용 블로그형",
            "title": str(manifest.get("title") or relative_latest.parent.name),
            "version": str(manifest.get("source_version") or ""),
            "validation": str(manifest.get("validation_status") or "unknown"),
            "vault": str(manifest.get("vault_publication_status") or "unknown"),
            "exported_at": str(manifest.get("exported_at") or ""),
            "copy": copy_link,
            "preview": preview_link,
            "folder": quote(relative_latest.as_posix(), safe="/"),
            "pdf": pdf_link,
        })
    entries.sort(key=lambda item: (item["project"].casefold(), item["profile"], item["title"].casefold()))
    cards = []
    for item in entries:
        cards.append(
            '<article class="item">'
            f'<p class="group">{html.escape(item["project"])} · {html.escape(item["profile"])}</p>'
            f'<h2>{html.escape(item["title"])}</h2>'
            f'<p>버전 {html.escape(item["version"])} · 검증 {html.escape(item["validation"])} · '
            f'Obsidian {html.escape(item["vault"])} · 내보낸 시각 {html.escape(item["exported_at"])}</p>'
            f'<p><a href="{item["copy"]}">본문 복사</a> · <a href="{item["preview"]}">미리보기</a>'
            f'{item["pdf"]} · <a href="{item["folder"]}">폴더 열기</a></p>'
            "</article>"
        )
    page = f'''{MANAGED_INDEX_MARKER}
<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>옵시디언 원고 목록</title>
<style>body{{font-family:"Malgun Gothic",sans-serif;max-width:960px;margin:40px auto;padding:0 24px;color:#222}}.item{{border:1px solid #ddd;padding:20px;margin:16px 0}}.group{{color:#666}}a{{color:#1769aa}}</style>
</head><body><h1>검증 완료 원고 출판함</h1><p>본문을 복사하고 번호순 이미지를 함께 사용하세요.</p>{''.join(cards)}</body></html>'''
    destination = root / "00 원고 목록.html"
    _atomic_write(destination, page.encode("utf-8"))
    return destination


def _refresh_vault_publication_status(bundle_dir: Path, status: str) -> bytes | None:
    manifest_path = bundle_dir / Path(*PurePosixPath(EXPORT_MANIFEST).parts)
    manifest = verify_bundle(bundle_dir)
    if manifest.get("vault_publication_status") == status:
        return None
    snapshot = manifest_path.read_bytes()
    manifest["vault_publication_status"] = status
    _atomic_write(
        manifest_path,
        (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )
    verify_bundle(bundle_dir)
    return snapshot


def _export_publication_bundle_locked(request: ExportRequest) -> dict:
    _load_runtime_dependencies()
    package = inspect_verified_package(request)
    _, publication_root = _safe_publication_boundary(request)
    _preflight_root_files(publication_root)
    item_root = _item_root(publication_root, package)
    item_root.mkdir(parents=True, exist_ok=True)
    recover_item_root(item_root)
    staging = item_root / f".staging-{uuid.uuid4().hex}"
    promotion: PromotionState | None = None
    latest_manifest_snapshot: bytes | None = None
    usage_path = publication_root / "00 사용 방법.txt"
    index_path = publication_root / "00 원고 목록.html"
    usage_snapshot = _snapshot_root_file(usage_path)
    index_snapshot = _snapshot_root_file(index_path)
    try:
        manifest = build_bundle(package, staging)
        promotion = _promote(package, publication_root, item_root, staging, manifest)
        if promotion.mode == "unchanged":
            latest_manifest_snapshot = _refresh_vault_publication_status(
                promotion.latest,
                package.vault_publication_status,
            )
        _write_usage(publication_root)
        regenerate_root_index(publication_root)
        _commit_promotion(promotion)
        incomplete_path = publication_root / INCOMPLETE_MARKER
        if incomplete_path.exists():
            incomplete_path.unlink()
    except Exception as error:
        if staging.exists():
            _safe_remove_owned(staging, item_root)
        if promotion is not None:
            try:
                _rollback_promotion(promotion)
            finally:
                if latest_manifest_snapshot is not None and promotion.latest.exists():
                    _atomic_write(
                        promotion.latest / Path(*PurePosixPath(EXPORT_MANIFEST).parts),
                        latest_manifest_snapshot,
                    )
                    verify_bundle(promotion.latest)
                _restore_root_file(usage_path, usage_snapshot)
                _restore_root_file(index_path, index_snapshot)
        _atomic_write(
            publication_root / INCOMPLETE_MARKER,
            (json.dumps({
                "status": "incomplete",
                "operation": "publication_export",
                "error": str(error),
                "read_only_report": True,
            }, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        )
        raise
    result = {
        "status": promotion.status,
        "profile": package.profile,
        "source_version": package.source_version,
        "latest_path": str(promotion.latest),
        "publication_root": str(publication_root),
        "vault_publication_status": package.vault_publication_status,
    }
    if promotion.status == "history_exported":
        result["history_path"] = str(item_root / "99 이전버전" / package.source_version)
    return result


def export_publication_bundle(request: ExportRequest) -> dict:
    _load_runtime_dependencies()
    package = inspect_verified_package(request)
    _, publication_root = _safe_publication_boundary(request)
    _preflight_root_files(publication_root)
    with _publication_lock(publication_root):
        return _export_publication_bundle_locked(request)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-version-dir", required=True)
    parser.add_argument("--publication-root", required=True)
    parser.add_argument("--project-destination-root", required=True)
    parser.add_argument("--vault-path")
    arguments = parser.parse_args(argv)
    request = ExportRequest(
        source_version_dir=Path(arguments.source_version_dir),
        publication_root=Path(arguments.publication_root),
        project_destination_root=arguments.project_destination_root,
        vault_path=Path(arguments.vault_path) if arguments.vault_path else None,
    )
    try:
        _load_runtime_dependencies()
        result = export_publication_bundle(request)
    except ModuleNotFoundError as error:
        missing = error.name or "runtime dependency"
        print(json.dumps({
            "status": "failed",
            "code": "python_dependency_missing",
            "error": f"python_dependency_missing: install the pinned runtime dependencies ({missing})",
        }, ensure_ascii=False))
        return 1
    except ExportError as error:
        print(json.dumps({"status": "failed", "code": error.code, "error": str(error)}, ensure_ascii=False))
        return 1
    except OSError:
        print(json.dumps({
            "status": "failed",
            "code": "filesystem_error",
            "error": "filesystem_error: publication export could not access a required file",
        }, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
