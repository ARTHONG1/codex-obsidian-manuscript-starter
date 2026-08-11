"""Deterministic routing for newly synthesized book A4 manuscripts."""

from __future__ import annotations

import argparse
import json
from typing import Any


_LEGACY_MARKERS = (
    "기존 양식",
    "레거시",
    "legacy",
    "v1",
    "V1",
)
_V2_MARKERS = ("v2", "V2", "2번 양식", "두 번째 양식")


def select_book_template(
    request_text: str,
    requested_template_version: int | None = None,
) -> dict[str, Any]:
    """Return the template contract for a new book A4 synthesis.

    New synthesis defaults to V3. V1/V2 are available only through an explicit
    historical selector or an explicit version request. Unknown versions are
    rejected instead of silently falling back to an older template.
    """
    if requested_template_version not in (None, 1, 2, 3):
        raise ValueError("unsupported_book_template_version")

    text = request_text or ""
    legacy_requested = any(marker in text for marker in _LEGACY_MARKERS)
    if requested_template_version == 1 or legacy_requested:
        return {"output_profile": "book_a4", "template_version": 1, "reason": "explicit_legacy_request"}

    if requested_template_version == 2:
        return {"output_profile": "book_a4", "template_version": 2, "reason": "explicit_v2_request"}

    if any(marker in text for marker in _V2_MARKERS):
        return {"output_profile": "book_a4", "template_version": 2, "reason": "explicit_v2_request"}

    if requested_template_version == 3:
        return {"output_profile": "book_a4", "template_version": 3, "reason": "explicit_v3_request"}

    return {"output_profile": "book_a4", "template_version": 3, "reason": "default_new_book_a4"}


def assert_new_book_a4_contract(manuscript: dict[str, Any]) -> None:
    """Fail closed when a new A4 synthesis has the wrong template shape."""
    if manuscript.get("output_profile") != "book_a4":
        raise ValueError("book_a4_output_profile_required")
    if manuscript.get("template_version") != 3:
        raise ValueError("book_template_contract_mismatch")
    if manuscript.get("editorial_quality_version") != 3 or not manuscript.get("practice_blocks") or not manuscript.get("editorial_review"):
        raise ValueError("book_template_contract_mismatch")
    if "steps" in manuscript or "tip" in manuscript:
        raise ValueError("book_template_contract_mismatch")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request-text", required=True)
    parser.add_argument("--template-version", type=int)
    args = parser.parse_args()
    try:
        result = select_book_template(args.request_text, args.template_version)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
