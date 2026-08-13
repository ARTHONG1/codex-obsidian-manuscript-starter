"""Build immutable local template candidates without copying sources."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from template_model import Template
from template_source import inspect_source


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
    manifests = []
    for source in sources:
        result = inspect_source(source)
        if result.code != "source_ready":
            raise TemplateCandidateError(result.code)
        manifests.append(result.to_dict())
    blocks = evidence.get("blocks", [{"component": "title", "section_id": "title"}])
    template = Template.from_dict({"display_name": display_name, "blocks": blocks})
    candidate_id = template.candidate_id()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    payload = template.to_dict() | {"candidate_id": candidate_id}
    (output / "template.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    source_payload = {"sources": manifests, "evidence": {"source_refs": evidence.get("source_refs", [])}}
    (output / "source-manifest.json").write_text(json.dumps(source_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "preview-content.json").write_text(json.dumps({"marker": "템플릿 검토용 미리보기", "sections": []}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"candidate_id": candidate_id, "status": "needs_review", "output_dir": str(output)}
