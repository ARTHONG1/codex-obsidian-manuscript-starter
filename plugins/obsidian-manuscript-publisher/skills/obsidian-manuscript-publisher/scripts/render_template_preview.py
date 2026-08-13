from __future__ import annotations

import html
from pathlib import Path
from typing import Any


def render_preview(template: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    display_name = html.escape(str(template.get("display_name", "사용자 양식 후보")))
    candidate_id = html.escape(str(template.get("candidate_id", "candidate")))
    page = f"""<!doctype html><html lang='ko'><meta charset='utf-8'><title>{display_name}</title><body><main><p>템플릿 검토용 미리보기</p><h1>{display_name}</h1><p>후보 ID: {candidate_id}</p><section>중립 예시 내용입니다.</section></main></body></html>"""
    html_path = output / "preview.html"
    html_path.write_text(page, encoding="utf-8")
    pdf_path = output / "preview.pdf"
    try:
        from reportlab.pdfgen import canvas
        pdf = canvas.Canvas(str(pdf_path))
        pdf.drawString(54, 780, "템플릿 검토용 미리보기")
        pdf.drawString(54, 760, str(template.get("display_name", "사용자 양식 후보")))
        pdf.save()
    except Exception:
        pdf_path.write_bytes(b"")
    return {"html": str(html_path), "pdf": str(pdf_path)}
