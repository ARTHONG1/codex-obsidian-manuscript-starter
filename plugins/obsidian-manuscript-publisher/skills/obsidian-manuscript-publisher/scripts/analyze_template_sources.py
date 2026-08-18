"""Canonical, parser-driven analysis pipeline for untrusted template examples."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from extract_docx_template import extract_docx_evidence
from extract_image_template import extract_image_evidence
from extract_pdf_template import extract_pdf_evidence
from template_source import TemplateSourceError, snapshot_source_set


class TemplateAnalysisError(ValueError):
    pass


def _load_observations(path: str | Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    source = Path(path)
    if not source.is_file():
        raise TemplateAnalysisError("observations_missing")
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TemplateAnalysisError("observations_invalid") from exc
    if not isinstance(value, list) or len(value) > 32:
        raise TemplateAnalysisError("observations_invalid")
    normalized = []
    for item in value:
        if not isinstance(item, dict):
            raise TemplateAnalysisError("observations_invalid")
        text = item.get("text", "")
        if not isinstance(text, str) or len(text) > 240 or "C:\\" in text or "\\\\" in text:
            raise TemplateAnalysisError("unsafe_observation")
        normalized.append({"kind": str(item.get("kind", "layout"))[:40], "text": text})
    return normalized


def analyze_sources(
    paths: list[str | Path],
    observations_path: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    try:
        with snapshot_source_set(paths) as snapshots:
            evidence: list[dict[str, Any]] = []
            for source in snapshots:
                suffix = Path(source.safe_name).suffix.lower()
                if suffix == ".docx":
                    value = extract_docx_evidence(source.path)
                elif suffix == ".pdf":
                    value = extract_pdf_evidence(source.path)
                else:
                    value = extract_image_evidence(source.path)
                evidence.append({"source": source.safe_name, "evidence": value})
            analysis = {
                "schema_version": 1,
                "status": "safe_for_preview",
                "source_manifest": [source.to_manifest() for source in snapshots],
                "evidence": evidence,
                "observations": _load_observations(observations_path),
                "layout_contract": {"blocks": [{"component": "title", "section_id": "title"}, {"component": "paragraphs", "section_id": "body"}]},
            }
    except TemplateSourceError as exc:
        raise TemplateAnalysisError(str(exc)) from None
    if output_dir is not None:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        (output / "source-analysis.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return analysis
