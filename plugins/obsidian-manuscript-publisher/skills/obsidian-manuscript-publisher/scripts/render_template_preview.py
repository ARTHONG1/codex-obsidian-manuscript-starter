"""Render a neutral custom-template preview with the same LayoutPlan renderer."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from render_custom_manuscript import _html, _markdown, _normalise, _pdf


def render_preview(template: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    plan_data = {
        "title": str(template.get("display_name", "사용자 양식 후보")),
        "blocks": template.get("blocks") or [{"component": "paragraphs", "text": "중립 예시 내용입니다."}],
    }
    plan = _normalise(plan_data)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="template-preview-", dir=str(output.parent)))
    try:
        html_path = staging / "preview.html"
        pdf_path = staging / "preview.pdf"
        html_path.write_text(_html(plan).replace("<main>", "<main><p>템플릿 검토용 미리보기</p>"), encoding="utf-8")
        _pdf(plan, pdf_path)
        final_html = output / html_path.name
        final_pdf = output / pdf_path.name
        if final_html.exists() or final_pdf.exists():
            raise ValueError("template_preview_version_exists")
        os.replace(html_path, final_html)
        os.replace(pdf_path, final_pdf)
        return {"html": str(final_html), "pdf": str(final_pdf), "status": "preview_ready"}
    finally:
        for path in staging.glob("*"):
            path.unlink(missing_ok=True)
        staging.rmdir()
