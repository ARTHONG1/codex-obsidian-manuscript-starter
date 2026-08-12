"""Canonical, side-effect-free view model for Book A4 template version 3.

Every V3 consumer (validator, renderer, desktop exporter, and finalizer) uses
this module instead of independently guessing whether a field resembles a V2
record.  The model deliberately keeps V3's list rows and string bodies intact.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


class BookV3Error(ValueError):
    """Raised when an input is not a canonical Book V3 document."""


def _mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise BookV3Error(f"{field} must be an object")
    return dict(value)


def _text(value: object, field: str, *, required: bool = True) -> str:
    if not isinstance(value, str):
        raise BookV3Error(f"{field} must be a string")
    normalized = value.strip()
    if required and not normalized:
        raise BookV3Error(f"{field} must not be empty")
    return normalized


def _visual(value: object, field: str, *, required: bool) -> dict[str, Any]:
    if value is None and not required:
        return {}
    visual = _mapping(value, field)
    if required and not str(visual.get("asset_id") or "").strip():
        raise BookV3Error(f"{field}.asset_id must not be empty")
    return visual


@dataclass(frozen=True)
class QuickReferenceRow:
    category: str
    item: str


@dataclass(frozen=True)
class ContentPanel:
    summary: str
    visual: dict[str, Any]
    title: str = ""
    qr_target: str = ""
    qr_label: str = ""


@dataclass(frozen=True)
class PracticeBlock:
    kind: str
    title: str
    body: str
    number: int | None = None
    step_id: str = ""
    visual: dict[str, Any] | None = None
    raw: dict[str, Any] | None = None


@dataclass(frozen=True)
class BookV3View:
    part: str
    chapter: str
    title: str
    subtitle: str
    chapter_intro: str
    source_markdown: str
    quick_reference: tuple[QuickReferenceRow, ...]
    preview: ContentPanel
    preparation: ContentPanel
    practice_blocks: tuple[PracticeBlock, ...]
    real_world_use: str
    real_world_use_panel: ContentPanel | None
    verification_note: str
    raw: dict[str, Any]

    @property
    def steps(self) -> tuple[PracticeBlock, ...]:
        return tuple(block for block in self.practice_blocks if block.kind == "step")

    @property
    def tips(self) -> tuple[PracticeBlock, ...]:
        return tuple(block for block in self.practice_blocks if block.kind == "tip")

    @property
    def visuals_in_render_order(self) -> tuple[tuple[str, dict[str, Any]], ...]:
        values: list[tuple[str, dict[str, Any]]] = [("preview", self.preview.visual), ("preparation", self.preparation.visual)]
        values.extend((f"step-{step.number:02d}", step.visual or {}) for step in self.steps)
        if self.real_world_use_panel and self.real_world_use_panel.visual:
            values.append(("real-world-use", self.real_world_use_panel.visual))
        return tuple(values)


def _panel(value: object, field: str, *, require_visual: bool, preview: bool = False) -> ContentPanel:
    panel = _mapping(value, field)
    summary_value = panel.get("summary")
    if summary_value is None and preview:
        summary_value = panel.get("result_summary")
    summary = _text(summary_value, f"{field}.summary")
    title = str(panel.get("title") or panel.get("result_title") or "").strip()
    qr_target = str(panel.get("qr_target") or panel.get("qr_url") or "").strip()
    qr_label = str(panel.get("qr_label") or "").strip()
    return ContentPanel(
        summary=summary,
        visual=_visual(panel.get("visual"), f"{field}.visual", required=require_visual),
        title=title,
        qr_target=qr_target,
        qr_label=qr_label,
    )


def _parse_rows(value: object) -> tuple[QuickReferenceRow, ...]:
    if not isinstance(value, list) or not value:
        raise BookV3Error("quick_reference must be a non-empty list")
    rows: list[QuickReferenceRow] = []
    for index, raw in enumerate(value, start=1):
        row = _mapping(raw, f"quick_reference[{index}]")
        rows.append(QuickReferenceRow(
            category=_text(row.get("category"), f"quick_reference[{index}].category"),
            item=_text(row.get("item"), f"quick_reference[{index}].item"),
        ))
    return tuple(rows)


def _parse_blocks(value: object) -> tuple[PracticeBlock, ...]:
    if not isinstance(value, list) or not value:
        raise BookV3Error("practice_blocks must be a non-empty list")
    blocks: list[PracticeBlock] = []
    expected_number = 1
    for index, raw in enumerate(value, start=1):
        block = _mapping(raw, f"practice_blocks[{index}]")
        kind = _text(block.get("type"), f"practice_blocks[{index}].type")
        if kind not in {"step", "tip"}:
            raise BookV3Error(f"practice_blocks[{index}].type must be step or tip")
        title = _text(block.get("title"), f"practice_blocks[{index}].title")
        body = _text(block.get("body"), f"practice_blocks[{index}].body")
        if kind == "step":
            number = block.get("number")
            if isinstance(number, bool) or not isinstance(number, int) or number != expected_number:
                raise BookV3Error(f"practice_blocks[{index}].number must be {expected_number}")
            expected_number += 1
            blocks.append(PracticeBlock(
                kind=kind,
                title=title,
                body=body,
                number=number,
                step_id=str(block.get("step_id") or "").strip(),
                visual=_visual(block.get("visual"), f"practice_blocks[{index}].visual", required=True),
                raw=block,
            ))
        else:
            blocks.append(PracticeBlock(kind=kind, title=title, body=body, raw=block))
    return tuple(blocks)


def parse_book_v3(value: object) -> BookV3View:
    """Parse one canonical V3 payload without coercing it into a V1/V2 shape."""

    data = _mapping(value, "manuscript")
    if data.get("output_profile") != "book_a4":
        raise BookV3Error("output_profile must be book_a4")
    if data.get("template_version") != 3 or data.get("editorial_quality_version") != 3:
        raise BookV3Error("template_version and editorial_quality_version must both be 3")

    real_panel_value = data.get("real_world_use_panel")
    real_panel = None
    if real_panel_value is not None:
        real_panel = _panel(real_panel_value, "real_world_use_panel", require_visual=False)

    return BookV3View(
        part=_text(data.get("part"), "part"),
        chapter=_text(data.get("chapter"), "chapter"),
        title=_text(data.get("title"), "title"),
        subtitle=str(data.get("subtitle") or "").strip(),
        chapter_intro=_text(data.get("chapter_intro"), "chapter_intro"),
        source_markdown=_text(data.get("source_markdown"), "source_markdown"),
        quick_reference=_parse_rows(data.get("quick_reference")),
        preview=_panel(data.get("preview"), "preview", require_visual=True, preview=True),
        preparation=_panel(data.get("preparation"), "preparation", require_visual=True),
        practice_blocks=_parse_blocks(data.get("practice_blocks")),
        real_world_use=_text(data.get("real_world_use"), "real_world_use"),
        real_world_use_panel=real_panel,
        verification_note=_text(str(data.get("verification_note") or ""), "verification_note", required=False),
        raw=data,
    )
