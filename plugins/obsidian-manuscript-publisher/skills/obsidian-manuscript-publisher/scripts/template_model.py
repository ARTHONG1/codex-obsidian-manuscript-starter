"""Bounded, declarative model for user-supplied manuscript templates."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any


ALLOWED_COMPONENTS = {
    "title", "section_label", "boxed_intro", "quick_table", "paragraphs",
    "step_sequence", "tip_box", "image", "caption", "caution", "page_break", "spacer",
}
_SAFE_TEXT = re.compile(r"^[^<>\\\x00-\x1f]{1,240}$")
_FORBIDDEN_KEYS = {"html", "css", "javascript", "script", "jinja", "command", "path", "url"}


def _check_value(value: Any, key: str = "") -> None:
    if key.lower() in _FORBIDDEN_KEYS:
        raise ValueError("unsafe_template_token")
    if isinstance(value, str):
        if not _SAFE_TEXT.fullmatch(value):
            raise ValueError("unsafe_template_token")
    elif isinstance(value, dict):
        for child_key, child_value in value.items():
            _check_value(child_value, str(child_key))
    elif isinstance(value, list):
        for child in value:
            _check_value(child, key)
    elif isinstance(value, (int, float, bool)) or value is None:
        return
    else:
        raise ValueError("unsafe_template_token")


@dataclass(frozen=True)
class Template:
    display_name: str
    blocks: tuple[dict[str, Any], ...]
    schema_version: int = 1
    template_profile: str = "custom_manuscript_template"
    status: str = "candidate"

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Template":
        if not isinstance(value, dict):
            raise ValueError("unsafe_template_token")
        _check_value(value)
        display_name = value.get("display_name", "")
        blocks = value.get("blocks", value.get("layout_contract", {}).get("blocks", []))
        if not isinstance(display_name, str) or not display_name.strip():
            raise ValueError("template_evidence_incomplete")
        if not isinstance(blocks, list):
            raise ValueError("unsafe_template_token")
        normalized: list[dict[str, Any]] = []
        for block in blocks:
            if not isinstance(block, dict) or block.get("component") not in ALLOWED_COMPONENTS:
                raise ValueError("unsafe_template_token")
            normalized.append(dict(block))
        return cls(
            display_name=display_name.strip(),
            blocks=tuple(normalized),
            schema_version=int(value.get("schema_version", 1)),
            template_profile=str(value.get("template_profile", "custom_manuscript_template")),
            status=str(value.get("status", "candidate")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "template_profile": self.template_profile,
            "display_name": self.display_name,
            "status": self.status,
            "blocks": [dict(block) for block in self.blocks],
        }

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def candidate_id(self) -> str:
        return "c-" + hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()[:16]


def candidate_id_for_inputs(inputs: dict[str, Any]) -> str:
    """Hash only canonical candidate inputs; timestamps and absolute paths are excluded by callers."""
    canonical = json.dumps(inputs, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "c-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
