from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from template_model import ALLOWED_COMPONENTS


_UNSAFE = re.compile(r"<|>|https?://|file:|\\\\|(?:^|[\\/])\.\.(?:$|[\\/])", re.IGNORECASE)


@dataclass(frozen=True)
class LayoutPlan:
    title: str
    blocks: tuple[dict[str, Any], ...]
    page_tokens: tuple[tuple[str, Any], ...] = ()
    style_tokens: tuple[tuple[str, Any], ...] = ()
    asset_hashes: tuple[str, ...] = ()

    @property
    def block_ids(self) -> tuple[str, ...]:
        return tuple(str(block["id"]) for block in self.blocks)

    def canonical_json(self) -> str:
        return json.dumps(
            {
                "title": self.title,
                "blocks": list(self.blocks),
                "page_tokens": dict(self.page_tokens),
                "style_tokens": dict(self.style_tokens),
                "asset_hashes": list(self.asset_hashes),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )


def compile_layout_plan(data: dict[str, Any], content: dict[str, Any] | None = None, assets: list[dict[str, Any]] | None = None) -> LayoutPlan:
    if not isinstance(data, dict):
        raise ValueError("custom_layout_contract_invalid")
    title = data.get("title", "사용자 양식 원고")
    if not isinstance(title, str) or _UNSAFE.search(title):
        raise ValueError("custom_layout_contract_invalid")
    blocks = data.get("blocks", [])
    if not isinstance(blocks, list):
        raise ValueError("custom_layout_contract_invalid")
    normalized = []
    seen = set()
    for block in blocks:
        if not isinstance(block, dict) or not isinstance(block.get("id"), str) or not block["id"]:
            raise ValueError("custom_layout_contract_invalid")
        if block["id"] in seen or block.get("component") not in ALLOWED_COMPONENTS:
            raise ValueError("custom_layout_contract_invalid")
        seen.add(block["id"])
        if block["component"] == "quick_table":
            headers, rows = block.get("headers"), block.get("rows")
            if not isinstance(headers, list) or not 1 <= len(headers) <= 20 or not isinstance(rows, list) or len(rows) > 1000:
                raise ValueError("custom_layout_contract_invalid")
            for row in [headers, *rows]:
                if not isinstance(row, list) or len(row) != len(headers) or any(not isinstance(cell, str) or _UNSAFE.search(cell) for cell in row):
                    raise ValueError("custom_layout_contract_invalid")
        for key in ("text", "caption", "alt"):
            if key in block and not isinstance(block[key], str):
                raise ValueError("custom_layout_contract_invalid")
        for key, value in block.items():
            if isinstance(value, str) and _UNSAFE.search(value):
                raise ValueError("custom_layout_contract_invalid")
            if key in {"font_size", "margin_top", "margin_bottom", "margin_left", "margin_right"}:
                if not isinstance(value, (int, float)) or not 0 <= value <= 120:
                    raise ValueError("custom_layout_contract_invalid")
        normalized.append(dict(block))
    page = data.get("page_tokens", {"width": 794, "height": 1123, "margin": 56})
    if not isinstance(page, dict) or any(type(value) not in (int, float) or not 0 <= value <= 2000 for value in page.values()):
        raise ValueError("custom_layout_contract_invalid")
    if min(page.get("width", 794), page.get("height", 1123)) - 2 * page.get("margin", 56) <= 16:
        raise ValueError("custom_layout_contract_invalid")
    style = data.get("style_tokens", {})
    if not isinstance(style, dict):
        raise ValueError("custom_layout_contract_invalid")
    hashes = []
    asset_records = assets if assets is not None else data.get("assets", [])
    if not isinstance(asset_records, list):
        raise ValueError("custom_layout_contract_invalid")
    for asset in asset_records:
        if not isinstance(asset, dict) or not re.fullmatch(r"[0-9a-f]{64}", str(asset.get("sha256", ""))):
            raise ValueError("custom_layout_contract_invalid")
        hashes.append(str(asset["sha256"]))
    return LayoutPlan(
        title=title,
        blocks=tuple(normalized),
        page_tokens=tuple(sorted(page.items())),
        style_tokens=tuple(sorted(style.items())),
        asset_hashes=tuple(hashes),
    )
