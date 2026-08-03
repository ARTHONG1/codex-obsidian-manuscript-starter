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
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
MIN_LANDSCAPE_RATIO = 1.5
MIN_IMAGE_WIDTH = 1200
INTERACTION_FIELDS = ("user_request", "codex_action", "user_check")
NOMINAL_STEP_ENDINGS = {
    "준비",
    "분석",
    "설계",
    "구성",
    "구현",
    "연결",
    "설정",
    "생성",
    "비교",
    "검증",
    "수정",
    "테스트",
    "설치",
    "배포",
    "실행",
    "적용",
    "활용",
    "정리",
}
SENTENCE_STYLE_ENDINGS = ("하기", "합니다", "하세요", "해보기", "해 봅니다", ".")
REPORT_TENSE_PATTERNS = ("구현했습니다", "완성했습니다", "추가했습니다", "요청했습니다", "되었습니다")
VISUAL_KINDS = {"ui_screen", "work_product", "workflow_diagram", "result_preview", "field_scene"}
QUALITY_FLAGS = (
    "purpose_match",
    "professional_layout",
    "legible_content",
    "no_generation_artifacts",
    "no_generic_ai_motifs",
)
REQUIRED_PROMPT_PHRASES = (
    "wide landscape composition, 16:9",
    "professional",
    "editorial",
)
REQUIRED_NEGATIVE_PROMPT_PHRASES = ("no robot", "no hologram", "no neon interface")
PROHIBITED_AI_MOTIFS = ("robot", "hologram", "glowing brain", "neon interface")


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


def validate_step_title(title: str, index: int) -> list[dict]:
    """Require a concise Korean noun phrase such as '업무 규칙 설계'."""
    value = str(title or "").strip()
    if not value:
        return [_issue("step_title_nominal_required", step=index)]
    if value.endswith(SENTENCE_STYLE_ENDINGS):
        return [_issue("step_title_sentence_style_forbidden", step=index)]
    if value.split()[-1] not in NOMINAL_STEP_ENDINGS:
        return [_issue("step_title_nominal_required", step=index)]
    return []


def validate_practical_prose(interaction: dict, index: int) -> list[dict]:
    """Reject only clear past-tense progress-report language in Step prose."""
    values = (str(interaction.get(field, "")) for field in INTERACTION_FIELDS)
    if any(pattern in value for value in values for pattern in REPORT_TENSE_PATTERNS):
        return [_issue("step_report_tense_forbidden", step=index)]
    return []


def validate_visual_metadata(visual: dict, *, step: int | None, asset_id: str) -> list[dict]:
    """Validate auditable purpose and human visual-review fields."""
    errors: list[dict] = []
    if visual.get("visual_kind") not in VISUAL_KINDS:
        errors.append(_issue("visual_kind_required", step=step, asset_id=asset_id))
    review = visual.get("quality_review")
    if not isinstance(review, dict) or any(review.get(flag) is not True for flag in QUALITY_FLAGS) or not str(review.get("review_note", "")).strip():
        errors.append(_issue("visual_quality_review_required", step=step, asset_id=asset_id))
    return errors


def quality_review_is_complete(review: object) -> bool:
    return isinstance(review, dict) and all(review.get(flag) is True for flag in QUALITY_FLAGS) and bool(str(review.get("review_note", "")).strip())


def prompt_is_professional(prompt: object) -> bool:
    """Reject vague or explicitly decorative AI-art prompts."""
    value = str(prompt or "").lower()
    if not all(phrase in value for phrase in REQUIRED_PROMPT_PHRASES + REQUIRED_NEGATIVE_PROMPT_PHRASES):
        return False
    for motif in PROHIBITED_AI_MOTIFS:
        if re.search(rf"(?<!no ){re.escape(motif)}", value):
            return False
    return True


def expected_caption_prefix(part: str, chapter: str, sequence: int) -> str:
    part_match = re.search(r"\d+", str(part))
    chapter_match = re.search(r"\d+", str(chapter))
    if not part_match or not chapter_match:
        return ""
    return f"그림 {part_match.group(0)}-{chapter_match.group(0).zfill(2)}-{sequence}. "


def validate_step(step: dict, index: int) -> list[dict]:
    """Validate step-only rules; asset-dependent rules are handled separately."""
    normalized = normalize_step(step)
    errors: list[dict] = []
    errors.extend(validate_step_title(normalized["title"], index))
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
    errors.extend(validate_practical_prose(interaction, index))
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
    if asset.get("visual_kind") not in VISUAL_KINDS:
        errors.append(_issue("asset_visual_kind_required", asset_id=asset_id))
    if not quality_review_is_complete(asset.get("quality_review")):
        errors.append(_issue("asset_quality_review_required", asset_id=asset_id))

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
    elif method == "generated_scene" and not prompt_is_professional(asset.get("prompt")):
        errors.append(_issue("unprofessional_prompt_contract", asset_id=asset_id))

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
                    if width < MIN_IMAGE_WIDTH:
                        errors.append(_issue("visual_minimum_resolution_required", asset_id=asset_id))
    return errors


def required_visuals(manuscript: dict) -> list[tuple[str, int | None, dict]]:
    """Return preview, every Step, and real-world-use visuals in render order."""
    visuals: list[tuple[str, int | None, dict]] = [
        ("preview", None, manuscript.get("preview", {}).get("visual") or {}),
    ]
    visuals.extend(
        ("step", index, step.get("visual") or {}) if isinstance(step, dict)
        else ("step", index, {})
        for index, step in enumerate(manuscript.get("steps", []), start=1)
    )
    visuals.append(("real_world_use", None, manuscript.get("real_world_use_visual") or {}))
    return visuals


def validate_package(manuscript: dict, manifest: dict, version_dir: Path) -> dict:
    """Return a deterministic validation result for a manuscript and asset manifest."""
    errors: list[dict] = []
    warnings: list[dict] = []
    required_types = {
        "output_profile": str,
        "source_markdown": str,
        "part": str,
        "chapter": str,
        "title": str,
        "chapter_intro": str,
        "quick_reference": dict,
        "preview": dict,
        "steps": list,
        "real_world_use": str,
        "real_world_use_visual": dict,
        "tip": str,
        "verification_note": str,
    }
    if not isinstance(manuscript, dict):
        return {"status": "invalid", "errors": [{"code": "top_level_object_required"}], "warnings": []}
    for field, expected_type in required_types.items():
        if field not in manuscript:
            errors.append(_issue(f"top_level_{field}_required"))
        elif not isinstance(manuscript[field], expected_type):
            errors.append(_issue(f"top_level_{field}_type"))
    if isinstance(manuscript.get("steps"), list):
        for index, step in enumerate(manuscript["steps"], start=1):
            if not isinstance(step, dict):
                errors.append(_issue("top_level_steps_item_type", step=index))
    if errors:
        errors = _sort_issues(errors)
        return {"status": "invalid", "errors": errors, "warnings": []}
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
    for sequence, (slot, step_index, visual) in enumerate(required_visuals(manuscript), start=1):
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
        errors.extend(validate_visual_metadata(visual, step=step_index, asset_id=asset_id))
        if visual_kind != asset.get("evidence_kind"):
            errors.append(_issue("visual_evidence_kind_mismatch", step=step_index, asset_id=asset_id))
        if visual_method != asset.get("method"):
            errors.append(_issue("visual_method_mismatch", step=step_index, asset_id=asset_id))
        if visual_kind not in KNOWN_EVIDENCE_KINDS:
            errors.append(_issue("unknown_evidence_kind", step=step_index, asset_id=asset_id))
        if visual_method not in KNOWN_METHODS:
            errors.append(_issue("unknown_evidence_method", step=step_index, asset_id=asset_id))
        if visual.get("visual_kind") != asset.get("visual_kind"):
            errors.append(_issue("visual_kind_mismatch", step=step_index, asset_id=asset_id))
        expected_prefix = expected_caption_prefix(manuscript.get("part", ""), manuscript.get("chapter", ""), sequence)
        caption = str(visual.get("caption", "")).strip()
        if not expected_prefix or not caption.startswith(expected_prefix) or len(caption) <= len(expected_prefix):
            errors.append(_issue("figure_caption_format_required", step=step_index, asset_id=asset_id))

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
    manuscript_bytes = manuscript_path.read_bytes()
    manifest_bytes = manifest_path.read_bytes()
    result = validate_package(
        json.loads(manuscript_bytes.decode("utf-8")),
        json.loads(manifest_bytes.decode("utf-8")),
        manuscript_path.parent,
    )
    result["validated_inputs"] = {
        "manuscript_sha256": hashlib.sha256(manuscript_bytes).hexdigest(),
        "asset_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
    }
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if result["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
