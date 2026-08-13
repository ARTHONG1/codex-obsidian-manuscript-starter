from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LayoutPlan:
    title: str
    blocks: tuple[dict[str, Any], ...]


def compile_layout_plan(data: dict[str, Any]) -> LayoutPlan:
    blocks = data.get("blocks", [])
    if not isinstance(blocks, list):
        raise ValueError("custom_layout_contract_invalid")
    return LayoutPlan(title=str(data.get("title", "사용자 양식 원고")), blocks=tuple(dict(block) for block in blocks))
