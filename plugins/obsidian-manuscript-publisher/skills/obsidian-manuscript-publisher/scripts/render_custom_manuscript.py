"""Render custom manuscripts from one validated, ordered LayoutPlan."""

from __future__ import annotations

import html
import os
import tempfile
from pathlib import Path
from typing import Any

from layout_plan import LayoutPlan, compile_layout_plan
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


FONT_PATH = Path(r"C:\Windows\Fonts\malgun.ttf")
FONT_NAME = "CustomMalgun"


def _normalise(data: dict[str, Any]) -> LayoutPlan:
    if not isinstance(data, dict):
        raise ValueError("custom_layout_contract_invalid")
    blocks = data.get("blocks", [])
    if not isinstance(blocks, list):
        raise ValueError("custom_layout_contract_invalid")
    normalized = []
    for index, block in enumerate(blocks, start=1):
        if not isinstance(block, dict):
            raise ValueError("custom_layout_contract_invalid")
        value = dict(block)
        value.setdefault("id", f"block-{index:03d}")
        normalized.append(value)
    value = dict(data)
    value["blocks"] = normalized
    return compile_layout_plan(value)


def _text(block: dict[str, Any]) -> str:
    value = block.get("text", "")
    if not isinstance(value, str):
        raise ValueError("custom_layout_contract_invalid")
    return value


def _markdown(plan: LayoutPlan) -> str:
    parts = [f"# {plan.title}", ""]
    for block in plan.blocks:
        component = block["component"]
        text = _text(block)
        if component == "page_break":
            parts.extend(["---", ""])
        elif component in {"title", "section_label"}:
            parts.extend([f"## {text}", ""])
        elif component in {"boxed_intro", "tip_box", "caution"}:
            parts.extend([f"> {text}", ""])
        else:
            parts.extend([text, ""])
    return "\n".join(parts)


def _html(plan: LayoutPlan) -> str:
    page = dict(plan.page_tokens)
    margin = float(page.get("margin", 56))
    width = float(page.get("width", 794))
    height = float(page.get("height", 1123))
    parts = [
        "<!doctype html><html lang='ko'><meta charset='utf-8'>",
        f"<style>@page{{size:{width}px {height}px;margin:{margin}px;}}main{{max-width:{max(1, width - 2 * margin)}px;margin:0 auto;}}.page-break{{break-before:page;page-break-before:always;}}blockquote{{border:1px solid #777;padding:8px;}}</style>",
        "<main>", f"<h1>{html.escape(plan.title)}</h1>",
    ]
    for block in plan.blocks:
        block_id = html.escape(block["id"], quote=True)
        text = html.escape(_text(block))
        component = block["component"]
        if component == "page_break":
            parts.append(f"<div data-block-id='{block_id}' class='page-break'></div>")
        elif component in {"title", "section_label"}:
            parts.append(f"<h2 data-block-id='{block_id}'>{text}</h2>")
        elif component in {"boxed_intro", "tip_box", "caution"}:
            parts.append(f"<blockquote data-block-id='{block_id}'>{text}</blockquote>")
        else:
            parts.append(f"<p data-block-id='{block_id}'>{text}</p>")
    parts.append("</main></html>")
    return "\n".join(parts)


def _register_font() -> str:
    if not FONT_PATH.is_file():
        raise ValueError("korean_font_missing")
    if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))
    return FONT_NAME


def _pdf(plan: LayoutPlan, path: Path) -> None:
    font = _register_font()
    page = dict(plan.page_tokens)
    width = float(page.get("width", 794))
    height = float(page.get("height", 1123))
    margin = float(page.get("margin", 56))
    points = lambda px: px * 72 / 96
    styles = {
        "body": ParagraphStyle("custom-body", fontName=font, fontSize=10, leading=16, alignment=TA_LEFT, spaceAfter=6),
        "heading": ParagraphStyle("custom-heading", fontName=font, fontSize=15, leading=22, alignment=TA_LEFT, spaceBefore=8, spaceAfter=8),
        "quote": ParagraphStyle("custom-quote", fontName=font, fontSize=10, leading=16, leftIndent=8 * mm, spaceAfter=8),
    }
    story = [Paragraph(html.escape(plan.title), styles["heading"])]
    for block in plan.blocks:
        text = html.escape(_text(block)).replace("\n", "<br/>")
        component = block["component"]
        if component == "page_break":
            story.append(PageBreak())
        elif component in {"title", "section_label"}:
            story.append(Paragraph(text, styles["heading"]))
        elif component in {"boxed_intro", "tip_box", "caution"}:
            table = Table([[Paragraph(text, styles["quote"])]], colWidths=[170 * mm])
            table.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, "#777777"), ("LEFTPADDING", (0, 0), (-1, -1), 6)]))
            story.extend([table, Spacer(1, 4)])
        else:
            story.append(Paragraph(text, styles["body"]))
    SimpleDocTemplate(
        str(path), pagesize=(points(width), points(height)),
        rightMargin=points(margin), leftMargin=points(margin),
        topMargin=points(margin), bottomMargin=points(margin),
    ).build(story)
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError("custom_pdf_empty")


def render_custom_manuscript(data: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    plan = _normalise(data)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="custom-manuscript-", dir=str(output.parent)))
    try:
        markdown_path = staging / "manuscript.md"
        html_path = staging / "manuscript.html"
        pdf_path = staging / "manuscript.pdf"
        markdown_path.write_text(_markdown(plan), encoding="utf-8")
        html_path.write_text(_html(plan), encoding="utf-8")
        _pdf(plan, pdf_path)
        finals = (output / markdown_path.name, output / html_path.name, output / pdf_path.name)
        for final in finals:
            if final.exists():
                raise ValueError("custom_output_version_exists")
        for source, final in zip((markdown_path, html_path, pdf_path), finals, strict=True):
            os.replace(source, final)
        return {"markdown": str(finals[0]), "html": str(finals[1]), "pdf": str(finals[2]), "layout_plan": plan.canonical_json()}
    finally:
        for path in staging.glob("*"):
            path.unlink(missing_ok=True)
        staging.rmdir()
