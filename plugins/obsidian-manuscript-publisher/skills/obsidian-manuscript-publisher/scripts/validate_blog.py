#!/usr/bin/env python3
"""Validate a source-grounded adaptive blog package."""

from __future__ import annotations

import hashlib
import json
import re
import os
import sys
import tempfile
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image as PillowImage
from PIL import ImageOps

try:
    from editorial_quality import compute_editorial_score, validate_master_voice, validate_visual_brief
except ImportError:  # pragma: no cover
    from editorial_quality import compute_editorial_score, validate_master_voice, validate_visual_brief


OUTPUT_PROFILE = "adaptive_blog"
MODE_ROLES = {
    "practical_guide": ("problem", "principle", "method", "evidence", "application"),
    "case_story": ("before", "turning_point", "process", "result", "lesson"),
    "insight_column": ("observation", "contrast", "principle", "example", "implication"),
}
EVIDENCE_KINDS = {"artifact", "error", "result", "comparison", "decision", "observation"}
VISUAL_METHODS = {"provided_asset", "generated_scene"}
VISUAL_KINDS = {"ui_screen", "work_product", "workflow_diagram", "result_preview", "field_scene"}
EVIDENCE_VISUAL_KINDS = {
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
QUALITY_FLAGS = (
    "purpose_match",
    "professional_layout",
    "legible_content",
    "no_generation_artifacts",
    "no_generic_ai_motifs",
)
HUMANITY_FLAGS = (
    "source_grounded_opening",
    "central_idea_consistency",
    "concrete_evidence",
    "visible_judgment",
    "varied_rhythm",
    "no_fabricated_experience",
)
CANNED_PATTERNS = (
    re.compile(r"안녕하세요(?:[.!?\s]|$)"),
    re.compile(r"오늘은.{0,100}(?:알아보겠습니다|살펴보겠습니다)", re.DOTALL),
    re.compile(r"결론적으로"),
    re.compile(r"도움이 되었기를 바랍니다"),
    re.compile(r"지금까지.{0,100}(?:알아보았습니다|살펴보았습니다)", re.DOTALL),
)
CLICKBAIT_PHRASES = (
    "완벽한",
    "혁신적인",
    "단 몇 분 만에",
    "무조건",
    "100%",
    "한 번에 끝",
)
FIRST_PERSON_MARKERS = ("저는", "제가", "직접 해보니", "느꼈습니다", "해봤습니다")
REQUIRED_PROMPT_PHRASES = (
    "wide landscape composition, 16:9",
    "professional",
    "editorial",
    "no robot",
    "no hologram",
    "no neon interface",
    "no floating icons",
    "no invented menus",
    "no unreadable korean",
)
PROHIBITED_AI_MOTIFS = (
    "robot",
    "hologram",
    "glowing brain",
    "neon interface",
    "floating icons",
    "invented menus",
    "unreadable korean",
)
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MIN_IMAGE_WIDTH = 1200
MIN_LANDSCAPE_RATIO = 1.5
MIN_SECTIONS = 5
MAX_SECTIONS = 7
MAX_SECTION_VISUALS = 4
GENERATED_VISUAL_DISCLOSURE = "AI 생성 설명 이미지"
ACTUAL_SCREENSHOT_CLAIMS = ("실제 화면", "실제 캡처", "실제 스크린샷", "actual screenshot")
RAW_PARAGRAPH_BLOCK_PATTERN = re.compile(r"(?m)^\s*(?:[-+*]\s+|\d+[.)]\s+|```|~~~)|</?[a-z][^>]*>", re.IGNORECASE)


def _issue(code: str, *, section: int | None = None, asset_id: str | None = None) -> dict:
    issue = {"code": code}
    if section is not None:
        issue["section"] = section
    if asset_id is not None:
        issue["asset_id"] = asset_id
    return issue


def _sort_issues(issues: list[dict]) -> list[dict]:
    return sorted(
        issues,
        key=lambda item: (item.get("section", 0), item.get("asset_id", ""), item["code"]),
    )


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _review_complete(review: object, flags: tuple[str, ...]) -> bool:
    return (
        isinstance(review, dict)
        and all(review.get(flag) is True for flag in flags)
        and _nonempty(review.get("review_note"))
    )


def _valid_reference_list(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(_nonempty(item) for item in value)


def _public_text(blog: dict) -> str:
    values: list[str] = []

    def append(value: object) -> None:
        if isinstance(value, str):
            values.append(value)

    def append_visual(value: object) -> None:
        if not isinstance(value, dict):
            return
        append(value.get("alt_text"))
        append(value.get("caption"))

    for field in ("title", "dek", "lead", "next_action", "closing", "meta_description"):
        append(blog.get(field))
    tags = blog.get("tags")
    if isinstance(tags, list):
        for tag in tags:
            append(tag)
    append_visual(blog.get("hero_visual"))
    sections = blog.get("sections")
    if isinstance(sections, list):
        for section in sections:
            if not isinstance(section, dict):
                continue
            append(section.get("heading"))
            append(section.get("role"))
            paragraphs = section.get("paragraphs")
            if isinstance(paragraphs, list):
                for paragraph in paragraphs:
                    append(paragraph)
            append_visual(section.get("visual"))
    return "\n".join(values)


def _uninformative_alt_text(value: object) -> bool:
    if not _nonempty(value):
        return False
    normalized = value.strip().casefold()
    if normalized in {"image", "photo", "picture", "사진", "이미지", "그림"}:
        return True
    return bool(re.fullmatch(r"[^/\\]+\.(?:png|jpe?g|gif|webp)", normalized))


def _prompt_is_professional(prompt: object) -> bool:
    value = str(prompt or "").lower()
    if not all(phrase in value for phrase in REQUIRED_PROMPT_PHRASES):
        return False
    return not any(re.search(rf"(?<!no ){re.escape(motif)}", value) for motif in PROHIBITED_AI_MOTIFS)


def _validate_structure(blog: dict) -> list[dict]:
    errors: list[dict] = []
    if blog.get("output_profile") != OUTPUT_PROFILE:
        errors.append(_issue("blog_profile_required"))

    mode = blog.get("mode")
    if mode not in MODE_ROLES:
        errors.append(_issue("blog_mode_invalid"))
    if not _nonempty(blog.get("mode_reason")):
        errors.append(_issue("mode_reason_required"))

    required_text = (
        "title",
        "slug",
        "audience",
        "dek",
        "lead",
        "core_idea",
        "next_action",
        "closing",
        "meta_description",
    )
    for field in required_text:
        if not _nonempty(blog.get(field)):
            errors.append(_issue(f"{field}_required"))
    if _nonempty(blog.get("slug")) and not SLUG_PATTERN.fullmatch(blog["slug"]):
        errors.append(_issue("blog_slug_invalid"))

    tags = blog.get("tags")
    if not isinstance(tags, list) or not tags or any(not _nonempty(tag) for tag in tags):
        errors.append(_issue("blog_tags_required"))

    sections = blog.get("sections")
    if not isinstance(sections, list) or not MIN_SECTIONS <= len(sections) <= MAX_SECTIONS:
        errors.append(_issue("blog_section_count_invalid"))
        sections = sections if isinstance(sections, list) else []

    roles: list[str] = []
    paragraph_counts: list[int] = []
    section_evidence_refs: list[tuple[int, list[str]]] = []
    for index, section in enumerate(sections, start=1):
        if not isinstance(section, dict):
            errors.append(_issue("blog_section_invalid", section=index))
            continue
        if not _nonempty(section.get("heading")):
            errors.append(_issue("section_heading_required", section=index))
        if "roles" in section:
            errors.append(_issue("section_roles_forbidden", section=index))
        raw_role = section.get("role")
        role = raw_role.strip() if isinstance(raw_role, str) else ""
        if not role:
            errors.append(_issue("section_role_required", section=index))
        elif mode in MODE_ROLES and role not in MODE_ROLES[mode]:
            errors.append(_issue("section_role_invalid", section=index))
        roles.append(role)
        paragraphs = section.get("paragraphs")
        if not isinstance(paragraphs, list) or not paragraphs or any(not _nonempty(value) for value in paragraphs):
            errors.append(_issue("section_paragraphs_required", section=index))
            paragraph_counts.append(0)
        else:
            paragraph_counts.append(len(paragraphs))
            if any(RAW_PARAGRAPH_BLOCK_PATTERN.search(value) for value in paragraphs):
                errors.append(_issue("paragraph_block_format_invalid", section=index))
        evidence_refs = section.get("evidence_refs")
        if not _valid_reference_list(evidence_refs):
            errors.append(_issue("section_evidence_refs_required", section=index))
        else:
            section_evidence_refs.append((index, evidence_refs))

    if mode in MODE_ROLES:
        required_roles = MODE_ROLES[mode]
        if not set(required_roles).issubset(set(roles)):
            errors.append(_issue("mode_roles_incomplete"))
        role_positions = {role: index for index, role in enumerate(required_roles)}
        known_positions = [role_positions[role] for role in roles if role in role_positions]
        if any(left > right for left, right in zip(known_positions, known_positions[1:])):
            errors.append(_issue("mode_roles_out_of_order"))
    if len(paragraph_counts) >= 3 and len(set(paragraph_counts)) == 1:
        errors.append(_issue("uniform_section_rhythm"))

    evidence_points = blog.get("evidence_points")
    if not isinstance(evidence_points, list) or len(evidence_points) < 2:
        errors.append(_issue("insufficient_evidence"))
        evidence_points = evidence_points if isinstance(evidence_points, list) else []
    evidence_ids: set[str] = set()
    for index, evidence in enumerate(evidence_points, start=1):
        if not isinstance(evidence, dict):
            errors.append(_issue("evidence_point_invalid", section=index))
            continue
        raw_evidence_id = evidence.get("evidence_id")
        evidence_id = raw_evidence_id.strip() if isinstance(raw_evidence_id, str) else ""
        if not evidence_id:
            errors.append(_issue("evidence_id_required", section=index))
        elif evidence_id in evidence_ids:
            errors.append(_issue("duplicate_evidence_id", section=index))
        else:
            evidence_ids.add(evidence_id)
        if evidence.get("kind") not in EVIDENCE_KINDS:
            errors.append(_issue("evidence_kind_invalid", section=index))
        if not _nonempty(evidence.get("detail")):
            errors.append(_issue("evidence_detail_required", section=index))
        refs = evidence.get("source_refs")
        if not isinstance(refs, list) or not refs or any(not _nonempty(ref) for ref in refs):
            errors.append(_issue("evidence_source_required", section=index))
        if not _nonempty(evidence.get("verification")):
            errors.append(_issue("evidence_verification_required", section=index))

    lead_refs = blog.get("lead_evidence_refs")
    if not _valid_reference_list(lead_refs):
        errors.append(_issue("lead_evidence_refs_required"))
    else:
        for reference in lead_refs:
            if reference not in evidence_ids:
                errors.append(_issue("evidence_reference_missing"))
    for section_index, references in section_evidence_refs:
        for reference in references:
            if reference not in evidence_ids:
                errors.append(_issue("evidence_reference_missing", section=section_index))

    first_person_refs = blog.get("first_person_evidence_refs")
    has_first_person = any(marker in _public_text(blog) for marker in FIRST_PERSON_MARKERS)
    if has_first_person or first_person_refs is not None:
        if not _valid_reference_list(first_person_refs) or any(reference not in evidence_ids for reference in first_person_refs):
            errors.append(_issue("evidence_reference_missing"))

    if not _review_complete(blog.get("humanity_review"), HUMANITY_FLAGS):
        errors.append(_issue("humanity_review_required"))
    return errors


def _validate_editorial(blog: dict) -> list[dict]:
    errors: list[dict] = []
    title = str(blog.get("title") or "")
    if any(phrase.lower() in title.lower() for phrase in CLICKBAIT_PHRASES):
        errors.append(_issue("clickbait_title_forbidden"))

    public_text = _public_text(blog)
    if any(pattern.search(public_text) for pattern in CANNED_PATTERNS):
        errors.append(_issue("canned_prose_forbidden"))

    evidence_by_id = {
        str(point.get("evidence_id")): point
        for point in blog.get("evidence_points", [])
        if isinstance(point, dict) and _nonempty(point.get("evidence_id"))
    }
    first_person_refs = blog.get("first_person_evidence_refs")
    has_first_person = any(marker in public_text for marker in FIRST_PERSON_MARKERS)
    if has_first_person or first_person_refs is not None:
        grounded_observation = _valid_reference_list(first_person_refs) and all(
            reference in evidence_by_id
            and evidence_by_id[reference].get("kind") == "observation"
            and _valid_reference_list(evidence_by_id[reference].get("source_refs"))
            and _nonempty(evidence_by_id[reference].get("verification"))
            for reference in first_person_refs
        )
        if not grounded_observation:
            errors.append(_issue("unsupported_first_person_experience"))

    has_generated_visual = any(
        isinstance(visual, dict) and visual.get("method") == "generated_scene"
        for _, visual in _visuals(blog)
    )
    if has_generated_visual and any(claim.casefold() in public_text.casefold() for claim in ACTUAL_SCREENSHOT_CLAIMS):
        errors.append(_issue("generated_visual_actual_screenshot_claim"))

    return errors


def _validate_visual_metadata(visual: object, *, section: int | None = None) -> list[dict]:
    if not isinstance(visual, dict):
        return [_issue("visual_required", section=section)]
    raw_asset_id = visual.get("asset_id")
    asset_id = raw_asset_id.strip() if isinstance(raw_asset_id, str) else ""
    errors: list[dict] = []
    if not asset_id:
        errors.append(_issue("visual_asset_id_required", section=section))
    method = visual.get("method")
    if method not in VISUAL_METHODS:
        errors.append(_issue("visual_method_invalid", section=section, asset_id=asset_id))
    if method == "generated_scene" and visual.get("disclosure") != GENERATED_VISUAL_DISCLOSURE:
        errors.append(_issue("generated_visual_disclosure_required", section=section, asset_id=asset_id))
    if method == "generated_scene":
        descriptive_text = f"{visual.get('alt_text', '')}\n{visual.get('caption', '')}".casefold()
        if GENERATED_VISUAL_DISCLOSURE.casefold() in descriptive_text:
            errors.append(_issue("generated_visual_public_disclosure_forbidden", section=section, asset_id=asset_id))
        if any(claim.casefold() in descriptive_text for claim in ACTUAL_SCREENSHOT_CLAIMS):
            errors.append(_issue("generated_visual_actual_screenshot_claim", section=section, asset_id=asset_id))
    if visual.get("visual_kind") not in VISUAL_KINDS:
        errors.append(_issue("visual_kind_required", section=section, asset_id=asset_id))
    if visual.get("evidence_kind") not in EVIDENCE_VISUAL_KINDS:
        errors.append(_issue("visual_evidence_kind_invalid", section=section, asset_id=asset_id))
    if visual.get("privacy_status") != "cleared":
        errors.append(_issue("visual_privacy_not_cleared", section=section, asset_id=asset_id))
    if not _nonempty(visual.get("image")):
        errors.append(_issue("visual_image_required", section=section, asset_id=asset_id))
    if not _nonempty(visual.get("alt_text")):
        errors.append(_issue("visual_alt_text_required", section=section, asset_id=asset_id))
    elif _uninformative_alt_text(visual.get("alt_text")):
        errors.append(_issue("visual_alt_text_uninformative", section=section, asset_id=asset_id))
    if not _nonempty(visual.get("caption")):
        errors.append(_issue("visual_caption_required", section=section, asset_id=asset_id))
    if not _review_complete(visual.get("quality_review"), QUALITY_FLAGS):
        errors.append(_issue("visual_quality_review_required", section=section, asset_id=asset_id))
    return errors


def _validate_asset(asset: dict, version_dir: Path) -> list[dict]:
    raw_asset_id = asset.get("asset_id")
    asset_id = raw_asset_id.strip() if isinstance(raw_asset_id, str) else ""
    errors: list[dict] = []
    if not asset_id:
        errors.append(_issue("asset_id_required"))
    method = asset.get("method")
    if method not in VISUAL_METHODS:
        errors.append(_issue("asset_method_invalid", asset_id=asset_id))
    if asset.get("visual_kind") not in VISUAL_KINDS:
        errors.append(_issue("asset_visual_kind_required", asset_id=asset_id))
    if asset.get("evidence_kind") not in EVIDENCE_VISUAL_KINDS:
        errors.append(_issue("asset_evidence_kind_invalid", asset_id=asset_id))
    if asset.get("privacy_status") != "cleared":
        errors.append(_issue("asset_privacy_not_cleared", asset_id=asset_id))
    if not _nonempty(asset.get("alt_text")):
        errors.append(_issue("asset_alt_text_required", asset_id=asset_id))
    elif _uninformative_alt_text(asset.get("alt_text")):
        errors.append(_issue("asset_alt_text_uninformative", asset_id=asset_id))
    if not _review_complete(asset.get("quality_review"), QUALITY_FLAGS):
        errors.append(_issue("asset_quality_review_required", asset_id=asset_id))
    if method == "generated_scene" and not _prompt_is_professional(asset.get("prompt")):
        errors.append(_issue("unprofessional_prompt_contract", asset_id=asset_id))
    if method == "generated_scene" and asset.get("disclosure") != GENERATED_VISUAL_DISCLOSURE:
        errors.append(_issue("generated_visual_disclosure_required", asset_id=asset_id))
    if method == "provided_asset":
        source = asset.get("source")
        if not isinstance(source, dict) or not _nonempty(source.get("kind")) or not _nonempty(source.get("reference")):
            errors.append(_issue("provided_asset_source_required", asset_id=asset_id))

    output_path = asset.get("output_path")
    expected_hash = str(asset.get("sha256") or "")
    if not _nonempty(output_path):
        errors.append(_issue("output_path_required", asset_id=asset_id))
        return errors
    raw_output_path = str(output_path)
    path_parts = raw_output_path.split("/")
    pure_path = PurePosixPath(raw_output_path)
    if (
        "\\" in raw_output_path
        or pure_path.is_absolute()
        or not path_parts
        or path_parts[0] != "assets"
        or any(part in {"", ".", ".."} for part in path_parts)
        or re.match(r"^[A-Za-z]:", raw_output_path)
    ):
        errors.append(_issue("asset_path_not_version_local", asset_id=asset_id))
        return errors
    if not SHA256_PATTERN.fullmatch(expected_hash):
        errors.append(_issue("sha256_invalid", asset_id=asset_id))

    version_root = version_dir.resolve()
    candidate = (version_root / str(output_path)).resolve()
    try:
        candidate.relative_to(version_root)
    except ValueError:
        errors.append(_issue("asset_path_not_version_local", asset_id=asset_id))
        return errors
    if candidate.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        errors.append(_issue("asset_format_invalid", asset_id=asset_id))
        return errors
    if not candidate.is_file():
        errors.append(_issue("asset_file_missing", asset_id=asset_id))
        return errors

    payload = candidate.read_bytes()
    valid_signature = (
        (candidate.suffix.lower() == ".png" and payload.startswith(b"\x89PNG\r\n\x1a\n"))
        or (candidate.suffix.lower() in {".jpg", ".jpeg"} and payload.startswith(b"\xff\xd8\xff"))
    )
    if not valid_signature:
        errors.append(_issue("asset_signature_invalid", asset_id=asset_id))
        return errors
    if SHA256_PATTERN.fullmatch(expected_hash) and hashlib.sha256(payload).hexdigest() != expected_hash:
        errors.append(_issue("asset_hash_mismatch", asset_id=asset_id))
    try:
        with PillowImage.open(candidate) as image:
            oriented = ImageOps.exif_transpose(image)
            width, height = oriented.size
            sample = oriented.convert("RGB")
            sample.thumbnail((64, 64))
            colors = sample.getcolors(maxcolors=4097)
            sample.close()
            if oriented is not image:
                oriented.close()
    except OSError:
        errors.append(_issue("asset_image_unreadable", asset_id=asset_id))
        return errors
    if width < MIN_IMAGE_WIDTH:
        errors.append(_issue("visual_minimum_resolution_required", asset_id=asset_id))
    if not height or width / height < MIN_LANDSCAPE_RATIO:
        errors.append(_issue("landscape_image_required", asset_id=asset_id))
    if colors is not None and len(colors) == 1:
        errors.append(_issue("visual_low_information", asset_id=asset_id))
    return errors


def _visuals(blog: dict) -> list[tuple[int | None, dict]]:
    values: list[tuple[int | None, dict]] = [(None, blog.get("hero_visual"))]
    for index, section in enumerate(blog.get("sections", []), start=1):
        if isinstance(section, dict) and section.get("visual") is not None:
            values.append((index, section.get("visual")))
    return values


def _validate_visuals(blog: dict, manifest: dict, version_dir: Path) -> list[dict]:
    errors: list[dict] = []
    raw_assets = manifest.get("assets")
    if not isinstance(raw_assets, list):
        return [_issue("asset_manifest_invalid")]

    assets: dict[str, dict] = {}
    output_paths: set[str] = set()
    for asset in raw_assets:
        if not isinstance(asset, dict):
            errors.append(_issue("asset_record_invalid"))
            continue
        raw_asset_id = asset.get("asset_id")
        asset_id = raw_asset_id.strip() if isinstance(raw_asset_id, str) else ""
        if asset_id in assets:
            errors.append(_issue("duplicate_asset_id", asset_id=asset_id))
        else:
            assets[asset_id] = asset
        raw_output_path = asset.get("output_path")
        output_path_key = raw_output_path.replace("\\", "/").casefold() if isinstance(raw_output_path, str) else ""
        if output_path_key:
            if output_path_key in output_paths:
                errors.append(_issue("duplicate_asset_output_path", asset_id=asset_id))
            output_paths.add(output_path_key)
        errors.extend(_validate_asset(asset, version_dir))

    visual_entries = _visuals(blog)
    if not isinstance(blog.get("hero_visual"), dict):
        errors.append(_issue("hero_visual_required"))
    if len(visual_entries) - 1 > MAX_SECTION_VISUALS:
        errors.append(_issue("section_visual_limit_exceeded"))

    used_ids: set[str] = set()
    for section_index, visual in visual_entries:
        errors.extend(_validate_visual_metadata(visual, section=section_index))
        if not isinstance(visual, dict):
            continue
        raw_asset_id = visual.get("asset_id")
        asset_id = raw_asset_id.strip() if isinstance(raw_asset_id, str) else ""
        if not asset_id:
            continue
        if asset_id in used_ids:
            errors.append(_issue("visual_asset_id_reused", section=section_index, asset_id=asset_id))
        used_ids.add(asset_id)
        asset = assets.get(asset_id)
        if asset is None:
            errors.append(_issue("required_asset_missing", section=section_index, asset_id=asset_id))
            continue
        for field in ("method", "visual_kind", "evidence_kind", "privacy_status", "alt_text"):
            if visual.get(field) != asset.get(field):
                errors.append(_issue(f"visual_{field}_mismatch", section=section_index, asset_id=asset_id))
        if visual.get("method") == "generated_scene" and visual.get("disclosure") != asset.get("disclosure"):
            errors.append(_issue("visual_disclosure_mismatch", section=section_index, asset_id=asset_id))
        image_path = str(visual.get("image") or "")
        if image_path != str(asset.get("output_path") or ""):
            errors.append(_issue("visual_output_path_mismatch", section=section_index, asset_id=asset_id))
    for asset_id in assets:
        if asset_id not in used_ids:
            errors.append(_issue("unused_asset_record", asset_id=asset_id))
    return errors


def validate_package(blog: object, manifest: object, version_dir: Path) -> dict:
    root_errors = []
    if not isinstance(blog, dict):
        root_errors.append(_issue("blog_root_invalid"))
    if not isinstance(manifest, dict):
        root_errors.append(_issue("asset_manifest_root_invalid"))
    if root_errors:
        return {"status": "invalid", "errors": _sort_issues(root_errors), "warnings": []}

    errors = []
    if isinstance(blog, dict) and blog.get("editorial_quality_version") == 3:
        if any(asset.get("method") != "generated_scene" for asset in (manifest.get("assets") or []) if isinstance(asset, dict)):
            errors.append(_issue("v3_generated_scene_required"))
        errors.extend(validate_master_voice(_public_text(blog)))
        score, score_errors = compute_editorial_score(blog.get("editorial_review"))
        errors.extend(score_errors)
        for _, visual in _visuals(blog):
            if isinstance(visual, dict):
                errors.extend(validate_visual_brief(visual.get("visual_brief"), asset_id=str(visual.get("asset_id", ""))))
    errors.extend(_validate_structure(blog))
    errors.extend(_validate_editorial(blog))
    errors.extend(_validate_visuals(blog, manifest, version_dir))
    errors = _sort_issues(errors)
    result = {"status": "ready" if not errors else "invalid", "errors": errors, "warnings": []}
    if isinstance(blog, dict) and blog.get("editorial_quality_version") == 3:
        result["editorial_score"] = score
    return result


def _atomic_write_report(report_path: Path, result: dict) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=".blog-validation.", suffix=".tmp", dir=report_path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, report_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print("usage: validate_blog.py BLOG_JSON ASSET_MANIFEST OUTPUT_REPORT", file=sys.stderr)
        return 2
    blog_path, manifest_path, report_path = map(Path, argv[1:])
    expected_report_path = blog_path.parent / "blog-validation.json"
    expected_manifest_path = blog_path.parent / "asset-manifest.json"
    if report_path.resolve() != expected_report_path.resolve():
        print("OUTPUT_REPORT must be blog-validation.json beside blog.json", file=sys.stderr)
        return 2
    if manifest_path.resolve() != expected_manifest_path.resolve():
        print("ASSET_MANIFEST must be asset-manifest.json beside blog.json", file=sys.stderr)
        return 2
    try:
        blog_bytes = blog_path.read_bytes()
        manifest_bytes = manifest_path.read_bytes()
        blog = json.loads(blog_bytes.decode("utf-8"))
        manifest = json.loads(manifest_bytes.decode("utf-8"))
        result = validate_package(blog, manifest, blog_path.parent)
        result["validated_inputs"] = {
            "blog_sha256": hashlib.sha256(blog_bytes).hexdigest(),
            "asset_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        }
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        result = {"status": "invalid", "errors": [{"code": "package_read_failed", "detail": str(error)}], "warnings": []}
    _atomic_write_report(report_path, result)
    return 0 if result["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
