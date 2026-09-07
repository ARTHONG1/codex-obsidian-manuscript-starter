"""Small deterministic quality gates shared by Book and Blog V3."""
from __future__ import annotations

import re
from typing import Any


def sentence_count(value: object) -> int:
    text = str(value or "").strip()
    if not text:
        return 0
    # Korean prose normally ends sentences with ., !, ?, or the Korean full stop.
    return max(1, len(re.findall(r"(?<!\d)[.!?](?:['\")\]]?)(?=\s|$)|다\.(?=\s|$)", text)))


def validate_sentence_range(value: object, minimum: int, maximum: int, code: str) -> list[dict]:
    count = sentence_count(value)
    return [] if minimum <= count <= maximum else [{"code": code, "count": count, "minimum": minimum, "maximum": maximum}]


def validate_master_voice(public_text: str) -> list[dict]:
    text = str(public_text or "")
    issues: list[dict] = []
    if re.search(r"(?:완벽하게|100%|아무것도 하지 않아도|무조건 성공)", text):
        issues.append({"code": "unsupported_promotional_absolute"})
    if len(re.findall(r"(?:구현했습니다|완성했습니다|생성했습니다)", text)) >= 3:
        issues.append({"code": "report_style_repetition"})
    return issues


def validate_visual_brief(brief: object, *, asset_id: str) -> list[dict]:
    if not isinstance(brief, dict):
        return [{"code": "visual_brief_required", "asset_id": asset_id}]
    required = ("purpose", "screen_state", "visible_elements", "reader_check", "style")
    issues = [{"code": "visual_brief_field_required", "field": key, "asset_id": asset_id} for key in required if not brief.get(key)]
    forbidden = set(brief.get("forbidden_overlays") or [])
    for item in ("red_box", "numbered_callout", "arrow"):
        if item not in forbidden:
            issues.append({"code": "instructional_overlay_forbidden", "asset_id": asset_id, "overlay": item})
    return issues


def compute_editorial_score(review: object) -> tuple[int, list[dict]]:
    weights = {"structure": 20, "specificity": 20, "voice": 15, "reproducibility": 15, "visuals": 15, "practice": 10, "safety": 5}
    if not isinstance(review, dict):
        return 0, [{"code": "editorial_review_required"}]
    issues = []
    total = 0
    for key, maximum in weights.items():
        value = review.get(key)
        if not isinstance(value, int) or not 0 <= value <= maximum:
            issues.append({"code": "editorial_score_category_invalid", "category": key})
        else:
            total += value
    if total < 85:
        issues.append({"code": "editorial_score_below_threshold", "score": total, "minimum": 85})
    for flag in ("no_unverified_claims", "no_sensitive_data", "visuals_reviewed"):
        if review.get(flag) is not True:
            issues.append({"code": "editorial_hard_failure", "flag": flag})
    return total, issues
