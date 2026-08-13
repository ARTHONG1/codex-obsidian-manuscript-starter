from __future__ import annotations

from typing import Any


def validate_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    safe = bool(candidate.get("safe_for_preview", False))
    unresolved = list(candidate.get("critical_unresolved", []))
    if not safe:
        return {"status": "unsafe_source", "safe_for_preview": False, "registration_ready": False, "errors": ["unsafe_template_source"]}
    status = "needs_review" if unresolved else "preview_ready"
    return {"status": status, "safe_for_preview": True, "registration_ready": status == "preview_ready", "errors": [], "critical_unresolved": unresolved}
