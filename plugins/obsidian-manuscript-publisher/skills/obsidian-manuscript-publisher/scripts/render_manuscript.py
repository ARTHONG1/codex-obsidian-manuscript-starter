"""Render a structured manuscript JSON file as print-ready A4 HTML and PDF."""

from __future__ import annotations

import html
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath

from book_v3 import BookV3View, parse_book_v3

from PIL import Image as PillowImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.utils import TimeStamp


FONT_PATH = Path(r"C:\Windows\Fonts\malgun.ttf")
GREEN = colors.HexColor("#B9F63A")
INK = colors.HexColor("#222222")
GRAY = colors.HexColor("#F4F4F0")
MIN_LANDSCAPE_RATIO = 1.5
OUTPUT_PROFILE = "book_a4"


class _DeterministicCanvas(pdfcanvas.Canvas):
    """Use ReportLab's stable metadata/ID mode for reproducible publication bytes."""

    def __init__(self, *args, **kwargs):
        kwargs["invariant"] = 1
        super().__init__(*args, **kwargs)
        self._doc._timeStamp = TimeStamp(1)
        self.setCreator("Obsidian Manuscript Publisher")
        self.setAuthor("")


def text(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def visual_fields(item: dict) -> tuple[str, str, str]:
    visual = item.get("visual") if isinstance(item.get("visual"), dict) else {}
    image = visual.get("image") or item.get("image") or ""
    caption = visual.get("caption") or item.get("caption") or ""
    method = visual.get("method") or ""
    return str(image), str(caption), str(method)


def interaction_text(step: dict, label: str) -> str:
    interaction = step.get("interaction") if isinstance(step.get("interaction"), dict) else {}
    fields = ("user_request", "codex_action", "user_check")
    missing = [field for field in fields if not str(interaction.get(field, "")).strip()]
    if missing:
        raise ValueError(f"{label} interaction is incomplete: {', '.join(missing)}")
    return " ".join(str(interaction[field]).strip() for field in fields)


def validate(data: dict) -> None:
    if data.get("template_version") == 3:
        parse_book_v3(data)
        return
    if data.get("template_version") == 2:
        if not isinstance(data.get("practice_blocks"), list) or not data["practice_blocks"]:
            raise ValueError("V2 practice_blocks must be a non-empty list")
        for block in data["practice_blocks"]:
            if block.get("type") == "step":
                body = block.get("body")
                if _v2_sentence_count(body) not in {2, 3}:
                    raise ValueError("V2 Step body must contain two or three sentences")
        return
    required = ["part", "chapter", "title", "chapter_intro", "quick_reference", "preview", "steps", "real_world_use", "tip", "verification_note"]
    missing = [name for name in required if not data.get(name)]
    if missing:
        raise ValueError(f"Missing manuscript fields: {', '.join(missing)}")
    if not isinstance(data["steps"], list) or not data["steps"]:
        raise ValueError("steps must be a non-empty list")
    for index, step in enumerate(data["steps"], start=1):
        interaction_text(step, f"Step {index}")


def _load_validator():
    validator_path = Path(__file__).resolve().with_name("validate_manuscript.py")
    spec = importlib.util.spec_from_file_location("obsidian_book_a4_validator", validator_path)
    if spec is None or spec.loader is None:
        raise ValueError("book_a4 validator could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _validation_ready(json_file: Path, data: dict) -> tuple[Path, dict, Path]:
    if not isinstance(data, dict) or data.get("output_profile") != OUTPUT_PROFILE:
        raise ValueError("render_manuscript.py requires output_profile book_a4")
    manifest_path = json_file.parent / "asset-manifest.json"
    report_path = json_file.parent / "asset-validation.json"
    if not manifest_path.is_file() or not report_path.is_file():
        raise ValueError("book_a4 asset manifest and validation report are required before rendering")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("status") != "ready":
        raise ValueError("book_a4 validation status must be ready before rendering")
    current_inputs = {
        "manuscript_sha256": hashlib.sha256(json_file.read_bytes()).hexdigest(),
        "asset_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    }
    if report.get("validated_inputs") != current_inputs:
        raise ValueError("book_a4 validation is stale; validate the current package again")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    fresh_report = _load_validator().validate_package(data, manifest, json_file.parent)
    if fresh_report.get("status") != "ready":
        raise ValueError("book_a4 package is stale or invalid; validate it again")

    source_markdown = str(data.get("source_markdown") or "").strip()
    source_name = PurePosixPath(source_markdown)
    if (
        not source_markdown
        or source_name.name != source_markdown
        or "\\" in source_markdown
        or source_name.suffix.lower() != ".md"
    ):
        raise ValueError("book_a4 source_markdown must name one version-root Markdown file")
    source_path = json_file.parent / source_markdown
    if not source_path.is_file():
        raise ValueError("book_a4 source_markdown file is required before rendering")
    return report_path, report, source_path


def _atomic_replace_files(files: tuple[tuple[Path, bytes], ...]) -> None:
    temporary_paths: list[Path] = []
    backup_paths: dict[Path, Path] = {}
    installed_paths: list[Path] = []
    try:
        for final_path, content in files:
            final_path.parent.mkdir(parents=True, exist_ok=True)
            handle, temporary_name = tempfile.mkstemp(
                prefix=f".{final_path.name}.", suffix=".tmp", dir=final_path.parent
            )
            temporary_path = Path(temporary_name)
            temporary_paths.append(temporary_path)
            with os.fdopen(handle, "wb") as stream:
                stream.write(content)
        for final_path, _ in files:
            if final_path.exists():
                handle, backup_name = tempfile.mkstemp(
                    prefix=f".{final_path.name}.", suffix=".bak", dir=final_path.parent
                )
                os.close(handle)
                backup_path = Path(backup_name)
                shutil.copy2(final_path, backup_path)
                backup_paths[final_path] = backup_path
        for temporary_path, (final_path, _) in zip(temporary_paths, files, strict=True):
            os.replace(temporary_path, final_path)
            installed_paths.append(final_path)
    except Exception:
        for final_path in reversed(installed_paths):
            backup_path = backup_paths.get(final_path)
            if backup_path is not None and backup_path.exists():
                os.replace(backup_path, final_path)
            elif final_path.exists():
                final_path.unlink()
        raise
    finally:
        for temporary_path in temporary_paths:
            if temporary_path.exists():
                temporary_path.unlink()
        for backup_path in backup_paths.values():
            if backup_path.exists():
                backup_path.unlink()


def _write_validated_render(
    output_directory: Path,
    html_content: str,
    pdf_bytes: bytes,
    report_path: Path,
    report: dict,
    source_path: Path,
) -> None:
    html_bytes = html_content.encode("utf-8")
    updated_report = dict(report)
    updated_report["validated_outputs"] = {
        source_path.name: hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "manuscript.html": hashlib.sha256(html_bytes).hexdigest(),
        "manuscript.pdf": hashlib.sha256(pdf_bytes).hexdigest(),
    }
    report_bytes = (json.dumps(updated_report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    _atomic_replace_files(
        (
            (output_directory / "manuscript.html", html_bytes),
            (output_directory / "manuscript.pdf", pdf_bytes),
            (report_path, report_bytes),
        )
    )


def required_image_path(item: dict, json_path: Path, label: str) -> Path:
    visual = item.get("visual") if isinstance(item.get("visual"), dict) else item
    if not isinstance(visual, dict) or visual.get("method") != "generated_scene":
        raise ValueError(f"{label} must use generated_scene")
    source = str(visual.get("image") or "").strip()
    if not source:
        raise ValueError(f"{label} image is required")
    caption = str(visual.get("caption") or "")
    if not caption.strip():
        raise ValueError(f"{label} caption is required")
    image_path = Path(source)
    if not image_path.is_absolute():
        image_path = json_path.parent / image_path
    image_path = image_path.resolve()
    if not image_path.is_file():
        raise ValueError(f"{label} image file does not exist: {image_path}")
    if image_path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        raise ValueError(f"{label} image must be PNG or JPEG")
    try:
        with PillowImage.open(image_path) as image:
            width, height = image.size
    except OSError as error:
        raise ValueError(f"{label} image is unreadable") from error
    if not width or not height or width / height < MIN_LANDSCAPE_RATIO:
        raise ValueError(f"{label} image must be landscape (width/height >= {MIN_LANDSCAPE_RATIO})")
    return image_path


def validate_required_visuals(data: dict, json_path: Path) -> None:
    if data.get("template_version") == 3:
        view = parse_book_v3(data)
        for slot, visual in view.visuals_in_render_order:
            required_image_path({"visual": visual}, json_path, slot)
        return
    if data.get("template_version") == 2:
        required_image_path(data["preview"], json_path, "preview")
        required_image_path(data["practice_preparation"], json_path, "preparation")
        for block in data["practice_blocks"]:
            if block.get("type") == "step":
                required_image_path(block, json_path, f"Step {block.get('number')}")
        if data.get("real_world_use_visual"):
            required_image_path(data["real_world_use_visual"], json_path, "real-world-use")
        return
    required_image_path(data["preview"], json_path, "preview")
    for index, step in enumerate(data["steps"], start=1):
        required_image_path(step, json_path, f"Step {index}")
    required_image_path(data.get("real_world_use_visual") or {}, json_path, "real-world-use")


def visual_html(item: dict, json_path: Path, output_directory: Path, label: str) -> str:
    image_path = required_image_path(item, json_path, label)
    caption = visual_fields(item)[1]
    relative_image = os.path.relpath(image_path, output_directory).replace(os.sep, "/")
    return f'''<figure class="visual-unit"><img src="{text(relative_image)}" alt="{text(caption)}">
    <figcaption>{text(caption)}</figcaption></figure>'''


def _v2_body(item: dict) -> str:
    body = item.get("body", [])
    if isinstance(body, list):
        return " ".join(str(sentence).strip() for sentence in body if str(sentence).strip())
    return str(body or "").strip()


def _v2_sentence_count(value: object) -> int:
    """Keep V2 renderer preflight aligned with its validator's list-or-string body contract."""

    if isinstance(value, list):
        return len([str(sentence).strip() for sentence in value if str(sentence).strip()])
    if not isinstance(value, str) or not value.strip():
        return 0
    return len([sentence for sentence in re.split(r"(?<=[.!?\u3002\uff01\uff1f])\s+", value.strip()) if sentence.strip()])


def render_v2_html(data: dict, json_path: Path, output_directory: Path) -> str:
    reference = "".join(
        f"<tr><th>{text(label)}</th><td>{text(value)}</td></tr>"
        for label, value in data["quick_reference"].items()
    )
    blocks: list[str] = []
    for block in data["practice_blocks"]:
        if block.get("type") == "step":
            index = block["number"]
            blocks.append(
                f'<section class="step"><h2>Step {index}. {text(block.get("title"))}</h2>'
                f'<p>{text(_v2_body(block))}</p>{visual_html(block, json_path, output_directory, f"Step {index} 이미지")}</section>'
            )
        elif block.get("type") == "tip":
            tip_text = _v2_body(block)
            blocks.append(f'<aside class="tip"><div class="label">[꿀팁 더하기]</div><p>{text(tip_text)}</p></aside>')
    preview = data["preview"]
    preparation = data["practice_preparation"]
    optional_real = visual_html(data["real_world_use_visual"], json_path, output_directory, "실전 활용하기 이미지") if data.get("real_world_use_visual") else ""
    return f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{text(data["title"])}</title>
<style>
@page {{ size:A4 portrait; margin:16mm 17mm 18mm; }} * {{ box-sizing:border-box; }} body {{ font-family:'Malgun Gothic',sans-serif; color:#222; font-size:10.5pt; line-height:1.75; margin:0; }} h1 {{ font-size:22pt; margin:0 0 15mm; }} h2 {{ font-size:13pt; margin:0 0 4mm; }} .label {{ display:inline-block; background:#b9f63a; border:1px solid #5d8420; font-weight:700; padding:1mm 3mm; margin:0 0 4mm; }} .box {{ border:1px solid #444; padding:5mm; margin-bottom:8mm; }} table {{ border-collapse:collapse; width:100%; margin-bottom:8mm; }} th,td {{ border:1px solid #444; padding:2.5mm 3mm; vertical-align:top; }} th {{ width:25%; background:#fafafa; }} .preview {{ border:1px solid #444; padding:4mm; margin-bottom:8mm; }} .step {{ break-inside:avoid; margin:0 0 8mm; }} .tip {{ break-inside:avoid; border:1px solid #444; background:#fafafa; padding:4mm; margin:0 0 8mm; }} .tip .label {{ margin-bottom:2mm; }} .visual-unit {{ break-inside:avoid; margin:3mm auto 4mm; }} .visual-unit img {{ display:block; width:100%; max-width:100%; height:auto; max-height:92mm; object-fit:contain; margin:0 auto; }} .visual-unit figcaption {{ color:#666; font-size:8.5pt; margin-top:1mm; }}
</style></head><body>
<h1>[{text(data["part"])} - {text(data["chapter"])}] {text(data["title"])}</h1>
<div class="label">[이번 챕터에서는]</div><div class="box">{text(data["chapter_intro"])}</div>
<div class="label">[한눈에 보기]</div><table>{reference}</table>
<div class="label">[미리 보기]</div><div class="preview"><strong>{text(preview.get("result_title"))}</strong><p>{text(preview.get("result_summary"))}</p>{visual_html(preview, json_path, output_directory, "결과물 이미지")}</div>
<div class="label">[실습 사전 준비]</div><p>{text(data["practice_preparation"].get("body"))}</p>{visual_html(preparation, json_path, output_directory, "실습 사전 준비 이미지")}
<div class="label">[실습하기]</div>{''.join(blocks)}
<div class="label">[실전 활용하기]</div><p>{text(data["real_world_use"])}</p>{optional_real}
</body></html>'''


def _v3_panel_item(panel) -> dict:
    return {"visual": panel.visual}


def _v3_reference_rows(view: BookV3View) -> str:
    return "".join(
        f"<tr><th>{text(row.category)}</th><td>{text(row.item)}</td></tr>"
        for row in view.quick_reference
    )


def render_v3_html(data: dict, json_path: Path, output_directory: Path) -> str:
    """Render canonical V3 directly; never adapt it to a V1/V2 payload."""

    view = parse_book_v3(data)
    blocks: list[str] = []
    for block in view.practice_blocks:
        if block.kind == "step":
            blocks.append(
                f'<section class="step"><h2>Step {block.number}. {text(block.title)}</h2>'
                f'<p>{text(block.body)}</p>{visual_html({"visual": block.visual or {}}, json_path, output_directory, f"Step {block.number} 이미지")}</section>'
            )
        else:
            blocks.append(
                f'<aside class="tip"><div class="label">[꿀팁 더하기]</div><h3>{text(block.title)}</h3><p>{text(block.body)}</p></aside>'
            )
    real_panel = ""
    if view.real_world_use_panel is not None:
        real_panel = f"<p>{text(view.real_world_use_panel.summary)}</p>"
        if view.real_world_use_panel.visual:
            real_panel += visual_html(_v3_panel_item(view.real_world_use_panel), json_path, output_directory, "실전 활용하기 이미지")
    qr = text(view.preview.qr_target or "자료 저장소 링크를 연결하세요")
    subtitle = f'<p class="subtitle">{text(view.subtitle)}</p>' if view.subtitle else ""
    note = f'<p class="note">※ {text(view.verification_note)}</p>' if view.verification_note else ""
    return f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{text(view.title)}</title>
<style>
@page {{ size:A4 portrait; margin:16mm 17mm 18mm; }} * {{ box-sizing:border-box; }} body {{ font-family:'Malgun Gothic',sans-serif; color:#222; font-size:10.5pt; line-height:1.75; margin:0; }} h1 {{ font-size:22pt; margin:0 0 3mm; }} h2 {{ font-size:13pt; margin:0 0 4mm; }} h3 {{ font-size:10.5pt; margin:0 0 2mm; }} .subtitle {{ margin:0 0 12mm; color:#555; }} .label {{ display:inline-block; background:#b9f63a; border:1px solid #5d8420; font-weight:700; padding:1mm 3mm; margin:0 0 4mm; }} .box {{ border:1px solid #444; padding:5mm; margin-bottom:8mm; }} table {{ border-collapse:collapse; width:100%; margin-bottom:8mm; }} th,td {{ border:1px solid #444; padding:2.5mm 3mm; vertical-align:top; }} th {{ width:25%; background:#fafafa; }} .preview {{ display:grid; grid-template-columns:28% 72%; border:1px solid #444; min-height:58mm; margin-bottom:8mm; }} .qr {{ border-right:1px solid #444; padding:4mm; display:flex; flex-direction:column; justify-content:center; text-align:center; }} .result {{ padding:4mm; }} .qr-content {{ color:#666; padding:4mm; overflow-wrap:anywhere; }} .step,.tip {{ break-inside:avoid; margin:0 0 8mm; }} .tip {{ border:1px solid #444; background:#fafafa; padding:4mm; }} .visual-unit {{ break-inside:avoid; margin:3mm auto 4mm; }} .visual-unit img {{ display:block; width:100%; max-width:100%; height:auto; max-height:92mm; object-fit:contain; margin:0 auto; }} .visual-unit figcaption {{ color:#666; font-size:8.5pt; margin-top:1mm; }} .note {{ color:#555; font-size:8.5pt; }}
</style></head><body>
<h1>[{text(view.part)} - {text(view.chapter)}] {text(view.title)}</h1>{subtitle}
<div class="label">[이번 챕터에서는]</div><div class="box">{text(view.chapter_intro)}</div>
<div class="label">[한눈에 보기]</div><table>{_v3_reference_rows(view)}</table>
<div class="label">[미리 보기]</div><div class="preview"><div class="qr"><strong>{text(view.preview.qr_label or 'QR코드')}</strong><div class="qr-content">{qr}</div></div><div class="result"><p>{text(view.preview.summary)}</p>{visual_html(_v3_panel_item(view.preview), json_path, output_directory, '미리 보기 이미지')}</div></div>
<div class="label">[실습 전 준비]</div><p>{text(view.preparation.summary)}</p>{visual_html(_v3_panel_item(view.preparation), json_path, output_directory, '실습 전 준비 이미지')}
<div class="label">[실습하기]</div>{''.join(blocks)}
<div class="label">[실전 활용하기]</div><p>{text(view.real_world_use)}</p>{real_panel}{note}
</body></html>'''


def render_html(data: dict, json_path: Path, output_directory: Path) -> str:
    if data.get("template_version") == 3:
        return render_v3_html(data, json_path, output_directory)
    if data.get("template_version") == 2:
        return render_v2_html(data, json_path, output_directory)
    reference = "".join(
        f"<tr><th>{text(label)}</th><td>{text(value)}</td></tr>"
        for label, value in data["quick_reference"].items()
    )
    steps = "".join(
        f'''<section class="step"><h2>Step {index}. {text(step.get("title"))}</h2>
        <p>{text(interaction_text(step, f"Step {index}"))}</p>{visual_html(step, json_path, output_directory, f"Step {index} 이미지")}</section>'''
        for index, step in enumerate(data["steps"], 1)
    )
    preview = data["preview"]
    qr = text(preview.get("qr_url") or "QR 또는 자료 저장소 링크를 연결하세요")
    return f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{text(data["title"])}</title>
<style>
@page {{ size: A4 portrait; margin: 16mm 17mm 18mm; }}
* {{ box-sizing:border-box; }} body {{ font-family:'Malgun Gothic','맑은 고딕',sans-serif; color:#222; font-size:10.5pt; line-height:1.75; margin:0; }}
h1 {{ font-size:22pt; margin:0 0 15mm; font-weight:700; }} h2 {{ font-size:13pt; margin:0 0 4mm; }}
.label {{ display:inline-block; background:#b9f63a; border:1px solid #5d8420; font-weight:700; padding:1mm 3mm; margin:0 0 4mm; }}
.box {{ border:1px solid #444; padding:5mm; margin:0 0 9mm; }} table {{ border-collapse:collapse; width:100%; margin:0 0 9mm; }} th,td {{ border:1px solid #444; padding:2.5mm 3mm; vertical-align:top; }} th {{ width:25%; background:#fafafa; text-align:center; }}
.preview {{ display:grid; grid-template-columns:28% 72%; border:1px solid #444; min-height:58mm; margin-bottom:9mm; }} .qr {{ border-right:1px solid #444; padding:4mm; display:flex; flex-direction:column; justify-content:center; text-align:center; }}
.result {{ padding:4mm; }} .qr-content {{ min-height:38mm; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; color:#666; padding:4mm; }}
.step {{ break-inside:avoid; margin:0 0 10mm; }} .visual-unit {{ break-inside:avoid; margin:3mm auto 4mm; }} .visual-unit img {{ display:block; width:100%; max-width:100%; height:auto; max-height:99mm; object-fit:contain; margin:0 auto; }} .visual-unit figcaption {{ color:#666; font-size:8.5pt; margin-top:1mm; }} .tip {{ border:1px solid #444; background:#fafafa; padding:5mm; white-space:pre-wrap; }} .note {{ font-size:8.5pt; color:#555; }}
</style></head><body>
<h1>[{text(data["part"])} - {text(data["chapter"])}] {text(data["title"])}</h1>
<div class="label">[이번 챕터에서는]</div><div class="box">{text(data["chapter_intro"])}</div>
<div class="label">[한눈에 보기]</div><table>{reference}</table>
<div class="label">[미리 보기]</div><div class="preview"><div class="qr"><strong>{text(preview.get("qr_label") or "QR코드")}</strong><div class="qr-content">{qr}</div></div><div class="result"><strong>{text(preview.get("result_title"))}</strong><p>{text(preview.get("result_summary"))}</p>{visual_html(preview, json_path, output_directory, "결과물 이미지")}</div></div>
<div class="label">[실습하기]</div>{steps}
<div class="label">[실전 활용하기]</div><p>{text(data["real_world_use"])}</p>
{visual_html(data.get("real_world_use_visual", {}), json_path, output_directory, "실전 활용하기 이미지")}
<div class="label">[꿀팁 더하기]</div><div class="tip">{text(data["tip"])}</div><p class="note">※ {text(data["verification_note"])}</p>
</body></html>'''


def styles() -> dict:
    if "Malgun" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("Malgun", str(FONT_PATH)))
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontName="Malgun", fontSize=20, leading=29, spaceAfter=22),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName="Malgun", fontSize=10, leading=18),
        "small": ParagraphStyle("small", parent=base["BodyText"], fontName="Malgun", fontSize=8, leading=13, textColor=colors.HexColor("#666666")),
        "step": ParagraphStyle("step", parent=base["Heading2"], fontName="Malgun", fontSize=13, leading=19, spaceAfter=4),
        "label": ParagraphStyle("label", parent=base["BodyText"], fontName="Malgun", fontSize=11, leading=15, alignment=TA_CENTER),
    }


def render_v2_pdf(data: dict, json_path: Path, output_path: Path) -> None:
    st = styles()
    doc = SimpleDocTemplate(str(output_path), pagesize=A4, leftMargin=17 * mm, rightMargin=17 * mm, topMargin=16 * mm, bottomMargin=18 * mm)
    story = [Paragraph(f"[{text(data['part'])} - {text(data['chapter'])}] {text(data['title'])}", st["title"])]

    def add_label(value: str) -> None:
        block = Table([[Paragraph(f"[{text(value)}]", st["label"])]], colWidths=[42 * mm])
        block.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GREEN), ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#5d8420")), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
        story.extend([block, Spacer(1, 3 * mm)])

    add_label("이번 챕터에서는")
    intro = Table([[Paragraph(text(data["chapter_intro"]), st["body"])]], colWidths=[176 * mm])
    intro.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, INK), ("PADDING", (0, 0), (-1, -1), 10)]))
    story.extend([intro, Spacer(1, 7 * mm)])
    add_label("한눈에 보기")
    rows = [[Paragraph(text(key), st["body"]), Paragraph(text(value), st["body"])] for key, value in data["quick_reference"].items()]
    quick = Table(rows, colWidths=[43 * mm, 133 * mm])
    quick.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.7, INK), ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#FAFAFA")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("PADDING", (0, 0), (-1, -1), 6)]))
    story.extend([quick, Spacer(1, 7 * mm)])
    add_label("미리 보기")
    preview = data["preview"]
    story.append(KeepTogether([Paragraph(text(preview.get("result_title")), st["body"]), Paragraph(text(preview.get("result_summary")), st["small"]), image_flowable(preview, json_path, "결과물 이미지", 176 * mm, 92 * mm), Paragraph(text(visual_fields(preview)[1]), st["small"]), Spacer(1, 6 * mm)]))
    add_label("실습 사전 준비")
    preparation = data["practice_preparation"]
    story.append(KeepTogether([Paragraph(text(preparation.get("body")), st["body"]), image_flowable(preparation, json_path, "실습 사전 준비 이미지"), Paragraph(text(visual_fields(preparation)[1]), st["small"]), Spacer(1, 6 * mm)]))
    add_label("실습하기")
    for block in data["practice_blocks"]:
        if block.get("type") == "step":
            story.append(KeepTogether([
                Paragraph(f"Step {block['number']}. {text(block.get('title'))}", st["step"]),
                Paragraph(text(_v2_body(block)), st["body"]),
                image_flowable(block, json_path, f"Step {block['number']} 이미지"),
                Paragraph(text(visual_fields(block)[1]), st["small"]),
                Spacer(1, 4 * mm),
            ]))
        else:
            tip_label = Table([[Paragraph("[꿀팁 더하기]", st["label"])]], colWidths=[42 * mm])
            tip_label.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GREEN), ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#5d8420")), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
            tip = Table([[Paragraph(text(_v2_body(block)), st["body"])]], colWidths=[176 * mm])
            tip.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, INK), ("BACKGROUND", (0, 0), (-1, -1), GRAY), ("PADDING", (0, 0), (-1, -1), 10)]))
            story.append(KeepTogether([tip_label, Spacer(1, 2 * mm), tip, Spacer(1, 5 * mm)]))
    add_label("실전 활용하기")
    story.append(Paragraph(text(data["real_world_use"]), st["body"]))
    if data.get("real_world_use_visual"):
        visual = data["real_world_use_visual"]
        story.extend([image_flowable(visual, json_path, "실전 활용하기 이미지"), Paragraph(text(visual_fields(visual)[1]), st["small"])])
    doc.build(story, canvasmaker=_DeterministicCanvas)


def _add_pdf_label(story: list, style: dict, value: str) -> None:
    block = Table([[Paragraph(f"[{text(value)}]", style["label"])]], colWidths=[42 * mm])
    block.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GREEN),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#5d8420")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([block, Spacer(1, 3 * mm)])


def render_v3_pdf(data: dict, json_path: Path, output_path: Path) -> None:
    """Render canonical V3 directly with V3 list rows and panel semantics."""

    view = parse_book_v3(data)
    st = styles()
    doc = SimpleDocTemplate(str(output_path), pagesize=A4, leftMargin=17 * mm, rightMargin=17 * mm, topMargin=16 * mm, bottomMargin=18 * mm)
    story: list = [Paragraph(f"[{text(view.part)} - {text(view.chapter)}] {text(view.title)}", st["title"])]
    if view.subtitle:
        story.extend([Paragraph(text(view.subtitle), st["small"]), Spacer(1, 5 * mm)])

    _add_pdf_label(story, st, "이번 챕터에서는")
    intro = Table([[Paragraph(text(view.chapter_intro), st["body"])]], colWidths=[176 * mm])
    intro.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, INK), ("PADDING", (0, 0), (-1, -1), 10)]))
    story.extend([intro, Spacer(1, 7 * mm)])

    _add_pdf_label(story, st, "한눈에 보기")
    rows = [[Paragraph(text(row.category), st["body"]), Paragraph(text(row.item), st["body"])] for row in view.quick_reference]
    quick = Table(rows, colWidths=[43 * mm, 133 * mm])
    quick.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.7, INK), ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#FAFAFA")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("PADDING", (0, 0), (-1, -1), 6)]))
    story.extend([quick, Spacer(1, 7 * mm)])

    _add_pdf_label(story, st, "미리 보기")
    qr_contents = [Paragraph(text(view.preview.qr_label or "QR코드"), st["body"]), Spacer(1, 2 * mm)]
    if view.preview.qr_target:
        qr_contents.extend([qr_flowable(view.preview.qr_target), Spacer(1, 1 * mm), Paragraph(text(view.preview.qr_target), st["small"])])
    else:
        qr_contents.append(Paragraph("자료 저장소 링크를 연결하세요", st["small"]))
    qr = Table([[qr_contents]], colWidths=[42 * mm], rowHeights=[50 * mm])
    qr.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.7, INK), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    preview_item = _v3_panel_item(view.preview)
    result = [Paragraph(text(view.preview.summary), st["body"]), Spacer(1, 3 * mm), image_flowable(preview_item, json_path, "미리 보기 이미지", 120 * mm, 72 * mm), Spacer(1, 1 * mm), Paragraph(text(visual_fields(preview_item)[1]), st["small"])]
    panel = Table([[qr, result]], colWidths=[42 * mm, 134 * mm])
    panel.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.7, INK), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (1, 0), (1, 0), 7), ("RIGHTPADDING", (1, 0), (1, 0), 7), ("TOPPADDING", (1, 0), (1, 0), 7), ("BOTTOMPADDING", (1, 0), (1, 0), 7)]))
    story.extend([panel, Spacer(1, 8 * mm)])

    _add_pdf_label(story, st, "실습 전 준비")
    preparation_item = _v3_panel_item(view.preparation)
    story.extend([Paragraph(text(view.preparation.summary), st["body"]), Spacer(1, 2 * mm), image_flowable(preparation_item, json_path, "실습 전 준비 이미지"), Paragraph(text(visual_fields(preparation_item)[1]), st["small"]), Spacer(1, 6 * mm)])

    _add_pdf_label(story, st, "실습하기")
    for block in view.practice_blocks:
        if block.kind == "step":
            step_item = {"visual": block.visual or {}}
            story.append(KeepTogether([
                Paragraph(f"Step {block.number}. {text(block.title)}", st["step"]),
                Paragraph(text(block.body), st["body"]), Spacer(1, 2 * mm),
                image_flowable(step_item, json_path, f"Step {block.number} 이미지"),
                Paragraph(text(visual_fields(step_item)[1]), st["small"]), Spacer(1, 5 * mm),
            ]))
        else:
            tip_label = Table([[Paragraph("[꿀팁 더하기]", st["label"])]], colWidths=[42 * mm])
            tip_label.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GREEN), ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#5d8420"))]))
            tip = Table([[Paragraph(f"<b>{text(block.title)}</b><br/>{text(block.body)}", st["body"])]], colWidths=[176 * mm])
            tip.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, INK), ("BACKGROUND", (0, 0), (-1, -1), GRAY), ("PADDING", (0, 0), (-1, -1), 10)]))
            story.append(KeepTogether([tip_label, Spacer(1, 2 * mm), tip, Spacer(1, 5 * mm)]))

    _add_pdf_label(story, st, "실전 활용하기")
    story.append(Paragraph(text(view.real_world_use), st["body"]))
    if view.real_world_use_panel is not None:
        story.append(Paragraph(text(view.real_world_use_panel.summary), st["body"]))
        if view.real_world_use_panel.visual:
            real_item = _v3_panel_item(view.real_world_use_panel)
            story.extend([image_flowable(real_item, json_path, "실전 활용하기 이미지"), Paragraph(text(visual_fields(real_item)[1]), st["small"])])
    if view.verification_note:
        story.extend([Spacer(1, 3 * mm), Paragraph("※ " + text(view.verification_note), st["small"])])
    doc.build(story, canvasmaker=_DeterministicCanvas)


def image_flowable(item: dict, json_path: Path, label: str, width: float = 176 * mm, max_height: float = 99 * mm):
    candidate = required_image_path(item, json_path, label)
    image = Image(str(candidate))
    image._restrictSize(width, max_height)
    return image


def qr_flowable(url: str):
    widget = QrCodeWidget(url)
    left, bottom, right, top = widget.getBounds()
    size = 24 * mm
    drawing = Drawing(size, size, transform=[size / (right - left), 0, 0, size / (top - bottom), 0, 0])
    drawing.add(widget)
    return renderPDF.GraphicsFlowable(drawing)


def render_pdf(data: dict, json_path: Path, output_path: Path) -> None:
    if data.get("template_version") == 3:
        return render_v3_pdf(data, json_path, output_path)
    if data.get("template_version") == 2:
        return render_v2_pdf(data, json_path, output_path)
    st = styles()
    doc = SimpleDocTemplate(str(output_path), pagesize=A4, leftMargin=17 * mm, rightMargin=17 * mm, topMargin=16 * mm, bottomMargin=18 * mm)
    story = [Paragraph(f"[{text(data['part'])} - {text(data['chapter'])}] {text(data['title'])}", st["title"])]

    def label(name: str):
        block = Table([[Paragraph(f"[{name}]", st["label"])]], colWidths=[42 * mm])
        block.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GREEN), ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#5d8420")), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
        story.extend([block, Spacer(1, 3 * mm)])

    label("이번 챕터에서는")
    intro = Table([[Paragraph(text(data["chapter_intro"]), st["body"])]], colWidths=[176 * mm])
    intro.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, INK), ("PADDING", (0, 0), (-1, -1), 10)]))
    story.extend([intro, Spacer(1, 7 * mm)])
    label("한눈에 보기")
    rows = [[Paragraph(text(key), st["body"]), Paragraph(text(value), st["body"])] for key, value in data["quick_reference"].items()]
    quick = Table(rows, colWidths=[43 * mm, 133 * mm])
    quick.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.7, INK), ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#FAFAFA")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("PADDING", (0, 0), (-1, -1), 6)]))
    story.extend([quick, Spacer(1, 7 * mm)])
    label("미리 보기")
    preview = data["preview"]
    qr_url = str(preview.get("qr_url") or "").strip()
    qr_contents = [Paragraph(text(preview.get("qr_label") or "QR코드"), st["body"]), Spacer(1, 2 * mm)]
    if qr_url:
        qr_contents.extend([qr_flowable(qr_url), Spacer(1, 1 * mm), Paragraph(text(qr_url), st["small"])])
    else:
        qr_contents.append(Paragraph("자료 저장소 링크를 연결하세요", st["small"]))
    qr = Table([[qr_contents]], colWidths=[42 * mm], rowHeights=[50 * mm])
    qr.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.7, INK), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    result = [Paragraph(text(preview.get("result_title")), st["body"]), Spacer(1, 2 * mm), Paragraph(text(preview.get("result_summary")), st["small"]), Spacer(1, 3 * mm), image_flowable(preview, json_path, "결과물 이미지", 120 * mm, 72 * mm), Spacer(1, 1 * mm), Paragraph(text(visual_fields(preview)[1]), st["small"])]
    panel = Table([[qr, result]], colWidths=[42 * mm, 134 * mm])
    panel.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.7, INK), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (1, 0), (1, 0), 7), ("RIGHTPADDING", (1, 0), (1, 0), 7), ("TOPPADDING", (1, 0), (1, 0), 7), ("BOTTOMPADDING", (1, 0), (1, 0), 7)]))
    story.extend([panel, Spacer(1, 8 * mm)])
    label("실습하기")
    for index, step in enumerate(data["steps"], 1):
        flow = [Paragraph(f"Step {index}. {text(step.get('title'))}", st["step"]), Paragraph(text(interaction_text(step, f"Step {index}")), st["body"]), Spacer(1, 2 * mm), image_flowable(step, json_path, f"Step {index} 이미지"), Spacer(1, 1 * mm), Paragraph(text(visual_fields(step)[1]), st["small"]), Spacer(1, 6 * mm)]
        story.append(KeepTogether(flow))
    label("실전 활용하기")
    real_world_visual = data.get("real_world_use_visual", {})
    story.append(KeepTogether([
        Paragraph(text(data["real_world_use"]), st["body"]),
        Spacer(1, 2 * mm),
        image_flowable(real_world_visual, json_path, "실전 활용하기 이미지"),
        Spacer(1, 1 * mm),
        Paragraph(text(visual_fields(real_world_visual)[1]), st["small"]),
        Spacer(1, 7 * mm),
    ]))
    tip_label = Table([[Paragraph("[꿀팁 더하기]", st["label"])]], colWidths=[42 * mm])
    tip_label.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GREEN), ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#5d8420")), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
    tip = Table([[Paragraph(text(data["tip"]), st["body"])]], colWidths=[176 * mm])
    tip.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, INK), ("BACKGROUND", (0, 0), (-1, -1), GRAY), ("PADDING", (0, 0), (-1, -1), 10)]))
    story.append(KeepTogether([tip_label, Spacer(1, 3 * mm), tip, Spacer(1, 3 * mm), Paragraph("※ " + text(data["verification_note"]), st["small"])]))
    doc.build(story, canvasmaker=_DeterministicCanvas)


def main(json_file: Path, output_directory: Path) -> None:
    json_file = json_file.resolve()
    output_directory = output_directory.resolve()
    data = json.loads(json_file.read_text(encoding="utf-8"))
    report_path, report, source_path = _validation_ready(json_file, data)
    validate(data)
    validate_required_visuals(data, json_file)
    output_directory.mkdir(parents=True, exist_ok=True)
    html_content = render_html(data, json_file, output_directory)
    handle, temporary_name = tempfile.mkstemp(
        prefix=".manuscript.pdf.", suffix=".tmp", dir=output_directory
    )
    os.close(handle)
    temporary_pdf = Path(temporary_name)
    try:
        render_pdf(data, json_file, temporary_pdf)
        pdf_bytes = temporary_pdf.read_bytes()
        _write_validated_render(
            output_directory,
            html_content,
            pdf_bytes,
            report_path,
            report,
            source_path,
        )
    finally:
        if temporary_pdf.exists():
            temporary_pdf.unlink()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: render_manuscript.py <manuscript.json> <output-directory>")
    try:
        main(Path(sys.argv[1]), Path(sys.argv[2]))
    except FileNotFoundError:
        print("ERROR: manuscript_input_missing", file=sys.stderr)
        raise SystemExit(1) from None
    except Exception as error:
        print(f"ERROR: {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from None
