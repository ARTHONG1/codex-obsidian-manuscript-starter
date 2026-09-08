"""Render custom manuscripts from one validated, ordered LayoutPlan."""

from __future__ import annotations

import html
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from layout_plan import LayoutPlan, compile_layout_plan
from custom_assets import Asset, reject_reparse_ancestors, snapshot_assets
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


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


def _md_cell(text: str) -> str:
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")


def _md_alt(text: str) -> str:
    return text.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]").replace("\n", " ")


def _markdown(plan: LayoutPlan, assets: dict[str, Asset] | None = None) -> str:
    assets = assets or {}
    parts = [f"# {_md_alt(plan.title)}", ""]
    for block in plan.blocks:
        component = block["component"]
        text = _text(block)
        if component in {"title", "section_label", "caption"}:
            text = _md_alt(text)
        if component == "image":
            asset = assets[block["asset_id"]]
            parts.extend([f"![{_md_alt(block.get('alt', ''))}]({asset.relative})", "", _md_alt(block.get("caption", "")), ""])
        elif component == "quick_table":
            rows = [block["headers"], ["---"] * len(block["headers"]), *block["rows"]]
            parts.extend(["| " + " | ".join(_md_cell(cell) for cell in row) + " |" for row in rows])
            parts.append("")
        elif component == "page_break":
            parts.extend(["---", ""])
        elif component in {"title", "section_label"}:
            parts.extend([f"## {text}", ""])
        elif component in {"boxed_intro", "tip_box", "caution"}:
            parts.extend([f"> {text}", ""])
        else:
            parts.extend([text, ""])
    return "\n".join(parts)


def _html(plan: LayoutPlan, assets: dict[str, Asset] | None = None) -> str:
    assets = assets or {}
    page = dict(plan.page_tokens)
    margin = float(page.get("margin", 56))
    width = float(page.get("width", 794))
    height = float(page.get("height", 1123))
    parts = [
        "<!doctype html><html lang='ko'><meta charset='utf-8'>",
        f"<style>@page{{size:{width}px {height}px;margin:{margin}px;}}main{{max-width:{width - 2 * margin}px;margin:0 auto;}}*{{box-sizing:border-box;}}figure,blockquote{{margin:8px 0;}}img{{max-width:100%;height:auto;}}table{{width:100%;table-layout:fixed;border-collapse:collapse;}}th,td{{border:1px solid #777;padding:6px;overflow-wrap:anywhere;}}.page-break{{break-before:page;page-break-before:always;}}blockquote{{border:1px solid #777;padding:8px;}}</style>",
        "<main>", f"<h1>{html.escape(plan.title)}</h1>",
    ]
    for block in plan.blocks:
        block_id = html.escape(block["id"], quote=True)
        text = html.escape(_text(block))
        component = block["component"]
        if component == "image":
            asset = assets[block["asset_id"]]
            alt = html.escape(block.get("alt", ""), quote=True)
            caption = html.escape(block.get("caption", ""))
            parts.append(f"<figure data-block-id='{block_id}'><img src='{asset.relative}' alt='{alt}'><figcaption>{caption}</figcaption></figure>")
        elif component == "quick_table":
            headers = "".join(f"<th>{html.escape(cell)}</th>" for cell in block["headers"])
            rows = "".join("<tr>" + "".join(f"<td>{html.escape(cell)}</td>" for cell in row) + "</tr>" for row in block["rows"])
            parts.append(f"<table data-block-id='{block_id}'><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table>")
        elif component == "page_break":
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


def _pdf(plan: LayoutPlan, path: Path, assets: dict[str, Asset] | None = None) -> None:
    assets = assets or {}
    font = _register_font()
    page = dict(plan.page_tokens)
    width = float(page.get("width", 794))
    height = float(page.get("height", 1123))
    margin = float(page.get("margin", 56))
    points = lambda px: px * 72 / 96
    # SimpleDocTemplate's frame reserves six points on each side.
    content_width = points(width - 2 * margin) - 12
    content_height = points(height - 2 * margin) - 12
    styles = {
        "body": ParagraphStyle("custom-body", fontName=font, fontSize=10, leading=16, alignment=TA_LEFT, spaceAfter=6),
        "heading": ParagraphStyle("custom-heading", fontName=font, fontSize=15, leading=22, alignment=TA_LEFT, spaceBefore=8, spaceAfter=8),
        "quote": ParagraphStyle("custom-quote", fontName=font, fontSize=10, leading=16, leftIndent=8 * mm, spaceAfter=8),
    }
    story = [Paragraph(html.escape(plan.title), styles["heading"])]
    for block in plan.blocks:
        text = html.escape(_text(block)).replace("\n", "<br/>")
        component = block["component"]
        if component == "image":
            asset = assets[block["asset_id"]]
            caption = None
            caption_height = 0
            if block.get("caption"):
                caption = Paragraph(html.escape(block["caption"]).replace("\n", "<br/>"), styles["body"])
                caption_height = caption.wrap(content_width, content_height)[1] + caption.getSpaceBefore() + caption.getSpaceAfter()
            available_height = content_height - caption_height
            if available_height <= 0:
                raise ValueError("custom_image_caption_too_tall")
            scale = min(content_width / asset.width, available_height / asset.height, 0.75)
            picture = Image(str(path.parent / asset.relative), width=asset.width * scale, height=asset.height * scale)
            picture.hAlign = "LEFT"
            story.append(KeepTogether([picture, caption]) if caption is not None else picture)
        elif component == "quick_table":
            rows = [[Paragraph(html.escape(cell).replace("\n", "<br/>"), styles["body"]) for cell in row] for row in [block["headers"], *block["rows"]]]
            table = Table(rows, colWidths=[content_width / len(block["headers"])] * len(block["headers"]), repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, "#777777"), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            story.extend([table, Spacer(1, 4)])
        elif component == "page_break":
            story.append(PageBreak())
        elif component in {"title", "section_label"}:
            story.append(Paragraph(text, styles["heading"]))
        elif component in {"boxed_intro", "tip_box", "caution"}:
            table = Table([[Paragraph(text, styles["quote"])]], colWidths=[content_width], hAlign="LEFT")
            table.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, "#777777"), ("LEFTPADDING", (0, 0), (-1, -1), 6)]))
            story.extend([table, Spacer(1, 4)])
        else:
            story.append(Paragraph(text, styles["body"]))
    SimpleDocTemplate(
        str(path), pagesize=(points(width), points(height)),
        invariant=1,
        rightMargin=points(margin), leftMargin=points(margin),
        topMargin=points(margin), bottomMargin=points(margin),
    ).build(story)
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError("custom_pdf_empty")


def render_custom_manuscript(data: dict[str, Any], output_dir: str | Path, *, asset_root: str | Path | None = None) -> dict[str, Any]:
    """Render one ordered plan; images require an explicit trusted local root.

    Asset records are {id, path, sha256}; image blocks reference asset_id.
    The returned assets list contains absolute paths for publication/export.
    No destination file is overwritten, even during concurrent promotion.
    """
    plan = _normalise(data)
    assets = snapshot_assets(data.get("assets", []), plan.blocks, asset_root)
    output = Path(os.path.abspath(output_dir))
    reject_reparse_ancestors(output)
    relatives = ["manuscript.md", "manuscript.html", "manuscript.pdf", *dict.fromkeys(asset.relative for asset in assets.values())]
    for relative in relatives:
        final = output / relative
        reject_reparse_ancestors(final)
        if final.exists():
            raise ValueError("custom_output_version_exists")
    # Private staging is independent of the destination: validation/render failures
    # cannot leave an empty output tree behind.
    staging = Path(tempfile.mkdtemp(prefix="custom-manuscript-"))
    created_files = []
    created_dirs = []

    def ensure_directory(directory: Path) -> None:
        reject_reparse_ancestors(directory)
        if directory.exists():
            if not directory.is_dir():
                raise ValueError("custom_output_invalid")
            return
        ensure_directory(directory.parent)
        try:
            directory.mkdir()
        except FileExistsError:
            reject_reparse_ancestors(directory)
            if not directory.is_dir():
                raise ValueError("custom_output_invalid")
        else:
            created_dirs.append(directory)

    try:
        markdown_path = staging / "manuscript.md"
        html_path = staging / "manuscript.html"
        pdf_path = staging / "manuscript.pdf"
        for asset in assets.values():
            target = staging / asset.relative
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(asset.payload)
        markdown_path.write_text(_markdown(plan, assets), encoding="utf-8")
        html_path.write_text(_html(plan, assets), encoding="utf-8")
        _pdf(plan, pdf_path, assets)
        for relative in relatives:
            final = output / relative
            ensure_directory(final.parent)
            reject_reparse_ancestors(final)
            try:
                stream = final.open("xb")
            except FileExistsError as exc:
                raise ValueError("custom_output_version_exists") from exc
            created_files.append(final)
            with stream, (staging / relative).open("rb") as source:
                shutil.copyfileobj(source, stream)
        return {"markdown": str(output / "manuscript.md"), "html": str(output / "manuscript.html"), "pdf": str(output / "manuscript.pdf"), "layout_plan": plan.canonical_json(), "assets": [str(output / relative) for relative in relatives[3:]]}
    except BaseException:
        for path in reversed(created_files):
            path.unlink(missing_ok=True)
        for directory in reversed(created_dirs):
            try:
                directory.rmdir()
            except OSError:
                pass  # Never remove unrelated files created by another writer.
        raise
    finally:
        shutil.rmtree(staging)
