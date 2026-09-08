"""Bounded local image snapshots for the custom manuscript renderer."""

from __future__ import annotations

import hashlib
import io
import os
import re
import stat
import warnings
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from PIL import Image, UnidentifiedImageError

MAX_ASSET_BYTES = 50 * 1024 * 1024
MAX_TOTAL_BYTES = 100 * 1024 * 1024
MAX_PIXELS = 50_000_000
MAX_ASSETS = 64
FORMATS = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".webp": "WEBP"}


def reject_reparse_ancestors(path: Path) -> None:
    """Inspect lexical ancestors before resolving, including Windows junctions."""
    for candidate in (path, *path.parents):
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
            raise ValueError("custom_unsafe_path")


@dataclass(frozen=True)
class Asset:
    relative: str
    payload: bytes
    width: int
    height: int


def snapshot_assets(records: object, blocks: tuple, asset_root: str | Path | None) -> dict[str, Asset]:
    if not isinstance(records, list) or len(records) > MAX_ASSETS:
        raise ValueError("custom_asset_manifest_invalid")
    references = [b.get("asset_id") for b in blocks if b["component"] == "image"]
    if not records and not references:
        return {}
    if asset_root is None:
        raise ValueError("custom_asset_root_required")
    root = Path(os.path.abspath(asset_root))
    reject_reparse_ancestors(root)
    if not root.is_dir():
        raise ValueError("custom_asset_root_invalid")
    result = {}
    total = 0
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("custom_asset_manifest_invalid")
        asset_id, relative, digest = record.get("id"), record.get("path"), record.get("sha256")
        if not isinstance(asset_id, str) or not asset_id or asset_id in result:
            raise ValueError("custom_asset_manifest_invalid")
        if not isinstance(relative, str) or not relative or re.search(r"[\\:%?#\x00-\x1f]", relative):
            raise ValueError("custom_unsafe_asset_path")
        parts = relative.split("/")
        if any(p in {"", ".", ".."} or p.endswith((".", " ")) for p in parts) or PurePosixPath(relative).is_absolute():
            raise ValueError("custom_unsafe_asset_path")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("custom_asset_manifest_invalid")
        source = root.joinpath(*parts)
        reject_reparse_ancestors(source)
        if not source.resolve().is_relative_to(root.resolve()) or source.suffix.lower() not in FORMATS:
            raise ValueError("custom_unsafe_asset_path")
        try:
            info = source.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_ASSET_BYTES:
                raise ValueError("custom_asset_too_large_or_invalid")
            with source.open("rb") as stream:
                opened = os.fstat(stream.fileno())
                reject_reparse_ancestors(source)
                if (info.st_dev, info.st_ino) != (opened.st_dev, opened.st_ino):
                    raise ValueError("custom_asset_changed")
                payload = stream.read(MAX_ASSET_BYTES + 1)
            total += len(payload)
            if len(payload) > MAX_ASSET_BYTES or total > MAX_TOTAL_BYTES:
                raise ValueError("custom_asset_too_large")
            if hashlib.sha256(payload).hexdigest() != digest:
                raise ValueError("custom_asset_hash_mismatch")
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(payload), formats=list(FORMATS.values())) as image:
                    width, height = image.size
                    if image.format != FORMATS[source.suffix.lower()] or getattr(image, "n_frames", 1) != 1:
                        raise ValueError("custom_asset_format_invalid")
                    if width * height > MAX_PIXELS:
                        raise ValueError("custom_asset_too_large")
                    image.verify()
                with Image.open(io.BytesIO(payload), formats=list(FORMATS.values())) as image:
                    image.load()
        except (OSError, UnidentifiedImageError, Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
            raise ValueError("custom_asset_invalid") from exc
        result[asset_id] = Asset(f"assets/{digest}{source.suffix.lower()}", payload, width, height)
    if any(not isinstance(ref, str) or ref not in result for ref in references):
        raise ValueError("custom_asset_reference_missing")
    if set(result) - set(references):
        raise ValueError("custom_asset_unreferenced")
    return result
