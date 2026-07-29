#!/usr/bin/env python3
"""Validate version-local manuscript evidence without external dependencies."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

from PIL import Image as PillowImage


KNOWN_EVIDENCE_KINDS = {
    "software_ui",
    "software_setting",
    "software_result",
    "document_result",
    "workflow",
    "comparison",
    "classroom_scene",
    "conceptual_scene",
    "provided_photo",
}
ACQUISITION_METHODS = {"generated_scene"}
KNOWN_METHODS = set(ACQUISITION_METHODS)
EXAMPLE_LABELS = ("예시 이미지", "예시 화면")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
MIN_LANDSCAPE_RATIO = 1.5
INTERACTION_FIELDS = ("user_request", "codex_action", "user_check")


def _issue(code: str, *, step: int | None = None, asset_id: str | None = None) -> dict:
    issue = {"code": code}
    if step is not None:
        issue["step"] = step
    if asset_id is not None:
        issue["asset_id"] = asset_id
    return issue


def _sort_issues(issues: list[dict]) -> list[dict]:
    return sorted(
        issues,
        key=lambda issue: (issue.get("step", 0), issue.get("asset_id", ""), issue["code"]),
    )


def normalize_step(step: dict) -> dict:
    """Return a shallow, stable representation of a manuscript step."""
    return {
        "title": step.get("title", ""),
        "body": step.get("body", ""),
        "step_kind": step.get("step_kind"),
        "build_action": step.get("build_action"),
        "artifact": step.get("artifact"),
        "completion_check": step.get("completion_check"),
        "interaction": step.get("interaction"),
        "deliverable": step.get("deliverable"),
        "visual": step.get("visual"),
    }


def validate_step(step: dict, index: int) -> list[dict]:
    """Validate step-only rules; asset-dependent rules are handled separately."""
    normalized = normalize_step(step)
    errors: list[dict] = []
    if normalized["step_kind"] != "build":
        errors.append(_issue("step_kind_required", step=index))
    if not str(normalized["build_action"] or "").strip():
        errors.append(_issue("build_action_required", step=index))
    artifact = normalized["artifact"] or {}
    if not str(artifact.get("name", "")).strip():
        errors.append(_issue("artifact_required", step=index))
    paths = artifact.get("paths")
    if not isinstance(paths, list) or not any(str(path).strip() for path in paths):
        errors.append(_issue("artifact_paths_required", step=index))
    if artifact.get("status") != "verified":
        errors.append(_issue("artifact_not_verified", step=index))
    if not str(normalized["completion_check"] or "").strip():
        errors.append(_issue("completion_check_required", step=index))
    interaction = normalized["interaction"] if isinstance(normalized["interaction"], dict) else {}
    for field in INTERACTION_FIELDS:
        if not str(interaction.get(field, "")).strip():
            errors.append(_issue(f"interaction_{field}_required", step=index))
    return errors


def validate_asset(asset: dict, version_dir: Path) -> list[dict]:
    """Validate asset metadata and, where applicable, its on-disk digest."""
    asset_id = asset.get("asset_id", "")
    method = asset.get("method")
    evidence_kind = asset.get("evidence_kind")
    errors: list[dict] = []
    if evidence_kind not in KNOWN_EVIDENCE_KINDS:
        errors.append(_issue("unknown_evidence_kind", asset_id=asset_id))
    if method not in KNOWN_METHODS:
        errors.append(_issue("unknown_evidence_method", asset_id=asset_id))

    output_path = asset.get("output_path")
    expected_hash = asset.get("sha256")
    if not output_path:
        errors.append(_issue("output_path_required", asset_id=asset_id))
    if not expected_hash:
        errors.append(_issue("sha256_required", asset_id=asset_id))
    elif not SHA256_PATTERN.fullmatch(str(expected_hash)):
        errors.append(_issue("sha256_invalid", asset_id=asset_id))
    if method == "generated_scene" and not asset.get("prompt"):
        errors.append(_issue("generation_prompt_required", asset_id=asset_id))

    if output_path:
        path = (version_dir / output_path).resolve()
        try:
            path.relative_to(version_dir.resolve())
        except ValueError:
            errors.append(_issue("asset_path_not_version_local", asset_id=asset_id))
            return errors
        if not path.is_file():
            errors.append(_issue("asset_file_missing", asset_id=asset_id))
        else:
            payload = path.read_bytes()
            suffix = path.suffix.lower()
            valid_signature = (
                (suffix == ".png" and payload.startswith(b"\x89PNG\r\n\x1a\n"))
                or (suffix in {".jpg", ".jpeg"} and payload.startswith(b"\xff\xd8\xff"))
            )
            if not valid_signature:
                errors.append(_issue("asset_signature_invalid", asset_id=asset_id))
            if expected_hash and hashlib.sha256(payload).hexdigest() != expected_hash:
                errors.append(_issue("asset_hash_mismatch", asset_id=asset_id))
            if valid_signature:
                try:
                    with PillowImage.open(path) as image:
                        width, height = image.size
                except OSError:
                    errors.append(_issue("asset_image_unreadable", asset_id=asset_id))
                else:
                    if not width or not height or width / height < MIN_LANDSCAPE_RATIO:
                        errors.append(_issue("landscape_image_required", asset_id=asset_id))
    return errors


def required_visuals(manuscript: dict) -> list[tuple[str, int | None, dict]]:
    """Return preview, every Step, and real-world-use visuals in render order."""
    visuals: list[tuple[str, int | None, dict]] = [
        ("preview", None, manuscript.get("preview", {}).get("visual") or {}),
    ]
    visuals.extend(
        ("step", index, step.get("visual") or {})
        for index, step in enumerate(manuscript.get("steps", []), start=1)
    )
    visuals.append(("real_world_use", None, manuscript.get("real_world_use_visual") or {}))
    return visuals


def validate_package(manuscript: dict, manifest: dict, version_dir: Path) -> dict:
    """Return a deterministic validation result for a manuscript and asset manifest."""
    errors: list[dict] = []
    warnings: list[dict] = []
    asset_list = manifest.get("assets", [])
    assets = {asset.get("asset_id"): asset for asset in asset_list}

    # A manifest is a publication record, not merely an index for Step images.
    # Validate every asset so unused or real-world-use visuals cannot bypass
    # provenance, version-local path, or hash requirements.
    seen_asset_ids: set[str] = set()
    for asset in asset_list:
        asset_id = asset.get("asset_id", "")
        if asset_id in seen_asset_ids:
            errors.append(_issue("duplicate_asset_id", asset_id=asset_id))
        seen_asset_ids.add(asset_id)
        errors.extend(validate_asset(asset, version_dir))

    for index, raw_step in enumerate(manuscript.get("steps", []), start=1):
        errors.extend(validate_step(raw_step, index))

    visual_asset_ids: set[str] = set()
    for slot, step_index, visual in required_visuals(manuscript):
        if not visual:
            code = {
                "preview": "preview_visual_required",
                "step": "step_visual_required",
                "real_world_use": "real_world_visual_required",
            }[slot]
            errors.append(_issue(code, step=step_index))
            continue
        asset_id = str(visual.get("asset_id", ""))
        if not asset_id:
            errors.append(_issue("visual_asset_id_required", step=step_index))
            continue
        if asset_id in visual_asset_ids:
            errors.append(_issue("visual_asset_id_reused", step=step_index, asset_id=asset_id))
        visual_asset_ids.add(asset_id)
        asset = assets.get(asset_id)
        if asset is None:
            errors.append(_issue("required_asset_missing", step=step_index, asset_id=asset_id))
            continue
        visual_kind = visual.get("evidence_kind")
        visual_method = visual.get("method")
        if visual_kind != asset.get("evidence_kind"):
            errors.append(_issue("visual_evidence_kind_mismatch", step=step_index, asset_id=asset_id))
        if visual_method != asset.get("method"):
            errors.append(_issue("visual_method_mismatch", step=step_index, asset_id=asset_id))
        if visual_kind not in KNOWN_EVIDENCE_KINDS:
            errors.append(_issue("unknown_evidence_kind", step=step_index, asset_id=asset_id))
        if visual_method not in KNOWN_METHODS:
            errors.append(_issue("unknown_evidence_method", step=step_index, asset_id=asset_id))
        if not any(label in str(visual.get("caption", "")) for label in EXAMPLE_LABELS):
            errors.append(_issue("illustration_label_required", step=step_index, asset_id=asset_id))

    errors = _sort_issues(errors)
    warnings = _sort_issues(warnings)
    if errors:
        status = "invalid"
    else:
        status = "ready"
    return {"status": status, "errors": errors, "warnings": warnings}


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print("usage: validate_manuscript.py MANUSCRIPT_JSON ASSET_MANIFEST OUTPUT_REPORT", file=sys.stderr)
        return 2
    manuscript_path, manifest_path, report_path = map(Path, argv[1:])
    result = validate_package(
        json.loads(manuscript_path.read_text(encoding="utf-8")),
        json.loads(manifest_path.read_text(encoding="utf-8")),
        manuscript_path.parent,
    )
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if result["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
