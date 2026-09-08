"""Validate and finalize custom output without overwriting an existing version."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

import publish_manuscript_version as publisher
from render_custom_manuscript import render_custom_manuscript
from resolve_custom_template import resolve_template

_VALIDATION = "custom-validation.json"
_OUTPUTS = {"manuscript.md", "manuscript.html", "manuscript.pdf", "layout-plan.json"}
_REPORTS = {_VALIDATION, "publication-validation.json", "finalization-report.json"}


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _editorial_review(record: dict) -> dict:
    """Retain a bounded editorial attestation; this is not an AI visual judge."""
    if 'editorial_review' not in record:
        return {}
    review = record['editorial_review']
    required = {'method', 'prompt', 'visual_kind', 'privacy_status', 'quality_review'}
    flags = {'relevant', 'professional', 'legible', 'artifact_free', 'no_generic_ai_motifs'}
    if not isinstance(review, dict) or set(review) != required:
        raise ValueError('custom_editorial_review_invalid')
    quality = review['quality_review']
    if (review['method'] != 'generated_scene' or review['privacy_status'] != 'cleared'
            or review['visual_kind'] not in {'ui_screen','work_product','workflow_diagram','result_preview','field_scene'}
            or not isinstance(quality, dict) or set(quality) != flags | {'note'}
            or any(quality[flag] is not True for flag in flags)):
        raise ValueError('custom_editorial_review_invalid')
    for text, limit in ((review['prompt'], 4000), (quality['note'], 1000)):
        if (not isinstance(text, str) or not text.strip() or len(text) > limit
                or re.search(r'[A-Za-z]:[/\\]|\\\\|file:|https?://|[\x00-\x08]', text, re.I)):
            raise ValueError('custom_editorial_review_invalid')
    return {'editorial_review': json.loads(json.dumps(review))}


def _payloads(root: Path) -> dict[str, bytes]:
    publisher._assert_safe_version_root(root)
    result = {}
    for path in root.rglob("*"):
        publisher._assert_safe_version_root(path)
        if not path.is_file():
            continue
        name = path.relative_to(root).as_posix()
        if name in _REPORTS:
            continue
        if name not in _OUTPUTS and not re.fullmatch(r"assets/[a-zA-Z0-9_-]+\.(?:png|jpg|jpeg|webp)", name):
            raise ValueError("unexpected_source_file")
        result[name] = path.read_bytes()
    if not _OUTPUTS.issubset(result):
        raise ValueError("custom_output_missing")
    if not result["manuscript.pdf"].startswith(b"%PDF-"):
        raise ValueError("custom_pdf_invalid")
    if not all(result.values()):
        raise ValueError("custom_output_empty")
    return result


def validate_custom_package(root: str | Path) -> dict:
    root = Path(root)
    payloads = _payloads(root)
    report = json.loads((root / _VALIDATION).read_text(encoding="utf-8"))
    if report.get("status") != "ready" or report.get("profile") != "custom_manuscript":
        raise ValueError("validation_not_ready")
    actual = {name: _digest(data) for name, data in payloads.items()}
    if report.get("files") != actual:
        raise ValueError("asset_hash_mismatch")
    return report


def validate_custom_snapshot(snapshots: list[tuple[str, bytes]], config, base_url=None) -> None:
    """Gate the exact immutable upload bytes, not files re-read afterwards."""
    payloads = dict(snapshots)
    try:
        report = json.loads(payloads.pop(_VALIDATION))
    except (KeyError, ValueError, TypeError) as error:
        raise ValueError('validation_not_ready') from error
    if report.get('status') != 'ready' or report.get('profile') != 'custom_manuscript':
        raise ValueError('validation_not_ready')
    binding = report.get('template')
    if not isinstance(binding, dict) or not binding.get('template_id'):
        raise ValueError('custom_template_required')
    if report.get('files') != {name: _digest(content) for name, content in payloads.items()}:
        raise ValueError('asset_hash_mismatch')
    if not _OUTPUTS.issubset(payloads) or any(name not in _OUTPUTS and not re.fullmatch(r'assets/[a-zA-Z0-9_-]+\.(?:png|jpg|jpeg|webp)', name) for name in payloads):
        raise ValueError('unexpected_source_file')
    snapshot = resolve_template(config, binding['template_id'], base_url, version=binding.get('version'))
    if snapshot['version'] != binding.get('version') or snapshot['files'] != binding.get('files'):
        raise ValueError('custom_template_snapshot_hash_mismatch')
    from render_custom_manuscript import _normalise
    plan = json.loads(payloads['layout-plan.json'])
    approved = _normalise(_bind_template(plan, snapshot))
    actual = _normalise(plan)
    if (actual.blocks, actual.page_tokens, actual.style_tokens) != (approved.blocks, approved.page_tokens, approved.style_tokens):
        raise ValueError('custom_template_structure_mismatch')
    # A caller can recompute a manifest hash. Prove that the actual documents
    # were rendered from this plan, rather than trusting a ready label alone.
    bindings = report.get('assets', [])
    if not isinstance(bindings, list):
        raise ValueError('custom_asset_manifest_invalid')
    for item in bindings:
        _editorial_review(item)
    with tempfile.TemporaryDirectory(prefix='custom-render-check-') as directory:
        temporary = Path(directory)
        source = temporary / 'source'
        source.mkdir()
        for name, content in payloads.items():
            if name.startswith('assets/'):
                target = source / name
                target.parent.mkdir(exist_ok=True)
                target.write_bytes(content)
        rendered = render_custom_manuscript(plan | {'assets': bindings}, temporary / 'rendered', asset_root=source)
        for key, name in (('markdown', 'manuscript.md'), ('html', 'manuscript.html'), ('pdf', 'manuscript.pdf')):
            if Path(rendered[key]).read_bytes() != payloads[name]:
                raise ValueError('custom_render_mismatch')
        if rendered['layout_plan'].encode('utf-8') != payloads['layout-plan.json']:
            raise ValueError('custom_render_mismatch')


def _desktop_stage(root: Path, destination: Path) -> None:
    publisher._assert_safe_version_root(destination)
    if destination.exists():
        raise ValueError("immutable_export_conflict")
    validation = validate_custom_package(root)
    payloads = _payloads(root)
    payloads[_VALIDATION] = (root / _VALIDATION).read_bytes()
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".custom-export-", dir=str(destination.parent)))
    try:
        for name, content in payloads.items():
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        validate_custom_package(stage)
        publisher._assert_safe_version_root(destination)
        if destination.exists():
            raise ValueError("immutable_export_conflict")
        # Windows rename refuses any existing destination. A sibling exclusive
        # lock serializes cooperating exporters on all platforms.
        lock = destination.parent / ("." + destination.name + ".export.lock")
        try:
            handle = lock.open("x")
        except FileExistsError as error:
            raise ValueError("immutable_export_conflict") from error
        try:
            with handle:
                if destination.exists():
                    raise ValueError("immutable_export_conflict")
                stage.rename(destination)
            if validate_custom_package(destination)["files"] != validation["files"]:
                raise ValueError("asset_hash_mismatch")
        finally:
            lock.unlink()
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def _bind_template(data: dict, snapshot: dict) -> dict:
    if snapshot.get("snapshot_verified") is not True:
        raise ValueError("custom_template_unverified")
    template = snapshot["template"]
    layout = template.get("layout_contract", {})
    expected = template.get("blocks", layout.get("blocks", []))
    blocks = data.get("blocks", [])
    if len(blocks) != len(expected) or any(a.get("component") != b.get("component") for a, b in zip(blocks, expected)):
        raise ValueError("custom_template_structure_mismatch")
    value = dict(data)
    bound = []
    content_keys = {"text", "headers", "rows", "items", "asset_id", "caption", "alt"}
    for actual, approved in zip(blocks, expected):
        item = dict(approved)
        item.update({key: val for key, val in actual.items() if key in content_keys})
        bound.append(item)
    value["blocks"] = bound
    for key in ("page_tokens", "style_tokens"):
        value[key] = template.get(key, layout.get(key, {}))
    if not value["page_tokens"]:
        value.pop("page_tokens")
    return value


def finalize_custom_publication(
    data: dict[str, Any],
    output_root: str | Path,
    desktop_root: str | Path | None = None,
    runtime_config: str | Path | None = None,
    vault_relative_version_dir: str | None = None,
    base_url: str | None = None,
    *,
    template_name: str | None = None,
    template_version: str | None = None,
    asset_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(output_root)
    for item in data.get('assets', []):
        _editorial_review(item)
    if not re.fullmatch(r"v0\.[1-9][0-9]*", root.name):
        raise ValueError("custom_version_required")
    publisher._assert_safe_version_root(root)
    if root.exists():
        raise ValueError("custom_output_version_exists")
    if desktop_root is not None:
        source_path, destination_path = Path(os.path.abspath(root)), Path(os.path.abspath(desktop_root))
        if destination_path.is_relative_to(source_path) or source_path.is_relative_to(destination_path):
            raise ValueError('custom_output_overlap')
        publisher._assert_safe_version_root(Path(desktop_root))
        if Path(desktop_root).exists():
            raise ValueError("immutable_export_conflict")
    snapshot = None
    if runtime_config is not None:
        if not template_name:
            raise ValueError("custom_template_required")
        if not vault_relative_version_dir or not vault_relative_version_dir.endswith("/" + root.name):
            raise ValueError("custom_vault_destination_required")
        publisher._assert_generic_destination(vault_relative_version_dir)
        snapshot = resolve_template(runtime_config, template_name, base_url, version=template_version)
        data = _bind_template(data, snapshot)
    elif template_name or template_version:
        raise ValueError("custom_template_requires_local_rest")
    kwargs = {"asset_root": asset_root} if asset_root is not None else {}
    rendered = render_custom_manuscript(data, root, **kwargs)
    (root / "layout-plan.json").write_text(rendered["layout_plan"], encoding="utf-8")
    payloads = _payloads(root)
    asset_paths = {Path(path).stem: Path(path).relative_to(Path(os.path.abspath(root))).as_posix() for path in rendered.get('assets', [])}
    validation = {
        "profile": "custom_manuscript", "status": "ready",
        "files": {name: _digest(content) for name, content in payloads.items()},
        "template": {"template_id": snapshot["template_id"], "version": snapshot["version"], "files": snapshot.get("files", {})} if snapshot else None,
        "assets": [{"id": item['id'], "path": asset_paths[item['sha256']], "sha256": item['sha256'], **_editorial_review(item)} for item in data.get('assets', [])],
    }
    (root / _VALIDATION).write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validate_custom_package(root)
    report = {
        "profile": "custom_manuscript", "status": "validated",
        "vault_publication_status": "not_attempted",
        "desktop_export_status": "not_attempted",
        "files": {key: Path(rendered[key]).name for key in ("markdown", "html", "pdf")},
    }
    if runtime_config is not None:
        try:
            result = publisher.publish_version(Path(runtime_config), root, vault_relative_version_dir, base_url)
            report["vault_publication_status"] = str(result.get("status", "unknown"))
        except Exception as error:
            report["vault_publication_status"] = "publication_failed"
            report["vault_publication_error_type"] = type(error).__name__
    if desktop_root is not None:
        try:
            _desktop_stage(root, Path(desktop_root))
            report["desktop_export_status"] = "exported"
        except Exception as error:
            report["desktop_export_status"] = "export_failed"
            report["desktop_export_error_type"] = type(error).__name__
    failed = report["vault_publication_status"] not in {"published", "not_attempted"} or report["desktop_export_status"] not in {"exported", "not_attempted"}
    report["status"] = "finalized_with_failure" if failed else "finalized"
    (root / "finalization-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
