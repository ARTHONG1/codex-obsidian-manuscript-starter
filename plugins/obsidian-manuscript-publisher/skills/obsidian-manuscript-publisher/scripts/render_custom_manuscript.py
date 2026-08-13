"""Render a validated custom manuscript package through one simple layout plan."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def _safe_text(value: Any) -> str:
    text = str(value)
    if "<script" in text.lower() or "</script" in text.lower():
        raise ValueError("unsafe_template_token")
    return text


def _blocks(data: dict[str, Any]) -> list[dict[str, Any]]:
    blocks = data.get("blocks", [])
    if not isinstance(blocks, list):
        raise ValueError("custom_layout_contract_invalid")
    return blocks


def render_custom_manuscript(data: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    title = _safe_text(data.get("title", "사용자 양식 원고"))
    markdown_parts = [f"# {title}\n"]
    html_parts = ["<!doctype html><html lang='ko'><meta charset='utf-8'><body>", f"<h1>{html.escape(title)}</h1>"]
    for block in _blocks(data):
        if not isinstance(block, dict):
            raise ValueError("custom_layout_contract_invalid")
        component = block.get("component")
        text = _safe_text(block.get("text", ""))
        if component == "paragraphs":
            markdown_parts.append(text + "\n")
            html_parts.append(f"<p>{html.escape(text)}</p>")
        elif component in {"title", "section_label"}:
            markdown_parts.append(f"## {text}\n")
            html_parts.append(f"<h2>{html.escape(text)}</h2>")
        elif component == "page_break":
            markdown_parts.append("\n---\n")
            html_parts.append("<hr>")
        elif component in {"boxed_intro", "tip_box", "caution"}:
            markdown_parts.append(f"> {text}\n")
            html_parts.append(f"<blockquote>{html.escape(text)}</blockquote>")
        else:
            markdown_parts.append(text + "\n")
            html_parts.append(f"<div>{html.escape(text)}</div>")
    html_parts.append("</body></html>")
    markdown_path = output / "manuscript.md"
    html_path = output / "manuscript.html"
    pdf_path = output / "manuscript.pdf"
    markdown_path.write_text("\n".join(markdown_parts), encoding="utf-8")
    html_path.write_text("\n".join(html_parts), encoding="utf-8")
    pdf = canvas.Canvas(str(pdf_path), pagesize=A4)
    y = 800
    for line in "\n".join(markdown_parts).splitlines():
        if y < 50:
            pdf.showPage()
            y = 800
        pdf.drawString(40, y, line[:110])
        y -= 16
    pdf.save()
    return {"markdown": str(markdown_path), "html": str(html_path), "pdf": str(pdf_path)}
