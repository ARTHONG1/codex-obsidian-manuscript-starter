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
    blocks = data.get("blocks", [])
    if not isinstance(data, dict) or not isinstance(blocks, list):
        raise ValueError("custom_layout_contract_invalid")
    normalized = []
    seen = set()
    for block in blocks:
        if not isinstance(block, dict) or not isinstance(block.get("id"), str) or not block["id"]:
            raise ValueError("custom_layout_contract_invalid")
        if block["id"] in seen or block.get("component") not in ALLOWED_COMPONENTS:
            raise ValueError("custom_layout_contract_invalid")
        seen.add(block["id"])
        for key, value in block.items():
            if isinstance(value, str) and _UNSAFE.search(value):
                raise ValueError("custom_layout_contract_invalid")
            if key in {"font_size", "margin_top", "margin_bottom", "margin_left", "margin_right"}:
                if not isinstance(value, (int, float)) or not 0 <= value <= 120:
                    raise ValueError("custom_layout_contract_invalid")
        normalized.append(dict(block))
    page = data.get("page_tokens", {"width": 794, "height": 1123, "margin": 56})
    if not isinstance(page, dict) or any(not isinstance(value, (int, float)) or not 0 <= value <= 2000 for value in page.values()):
        raise ValueError("custom_layout_contract_invalid")
    style = data.get("style_tokens", {})
    if not isinstance(style, dict):
        raise ValueError("custom_layout_contract_invalid")
    hashes = []
    for asset in assets or data.get("assets", []):
        if not isinstance(asset, dict) or not re.fullmatch(r"[0-9a-f]{64}", str(asset.get("sha256", ""))):
            raise ValueError("custom_layout_contract_invalid")
        hashes.append(str(asset["sha256"]))
    return LayoutPlan(
        title=str(data.get("title", "사용자 양식 원고")),
        blocks=tuple(normalized),
        page_tokens=tuple(sorted(page.items())),
        style_tokens=tuple(sorted(style.items())),
        asset_hashes=tuple(hashes),
    )
