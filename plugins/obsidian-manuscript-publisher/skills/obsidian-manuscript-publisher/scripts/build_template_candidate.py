"""Build immutable local template candidates without copying sources."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from analyze_template_sources import analyze_sources, TemplateAnalysisError
from template_model import Template


class TemplateCandidateError(ValueError):
    pass


def require_approval(request: dict[str, Any]) -> None:
    candidate_id = request.get("candidate_id")
    approved = request.get("approved_candidate_id")
    if not candidate_id or candidate_id != approved:
        raise TemplateCandidateError("template_approval_required")


def build_candidate(display_name: str, sources: list[str | Path], evidence: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    if not sources:
        raise TemplateCandidateError("template_evidence_incomplete")
    try:
        analysis = analyze_sources(sources, output_dir=output_dir)
    except TemplateAnalysisError as exc:
        raise TemplateCandidateError(str(exc)) from exc
    blocks = analysis["layout_contract"]["blocks"]
    template = Template.from_dict({"display_name": display_name, "blocks": blocks})
    canonical = json.dumps(
        {"template": template.to_dict(), "analysis": analysis},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    candidate_id = "c-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    payload = template.to_dict() | {"candidate_id": candidate_id}
    (output / "template.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    source_payload = {"sources": analysis["source_manifest"], "evidence": analysis["evidence"]}
    (output / "source-manifest.json").write_text(json.dumps(source_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "preview-content.json").write_text(json.dumps({"marker": "템플릿 검토용 미리보기", "sections": []}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"candidate_id": candidate_id, "status": "needs_review", "output_dir": str(output)}
