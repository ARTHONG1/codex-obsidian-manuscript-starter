"""Security-first inspection for user-supplied manuscript template examples."""

from __future__ import annotations

import hashlib
import mimetypes
from dataclasses import dataclass
from pathlib import Path


MAX_SOURCE_BYTES = 50 * 1024 * 1024
MAX_SOURCE_FILES = 8
MAX_TOTAL_SOURCE_BYTES = 100 * 1024 * 1024
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".png", ".jpg", ".jpeg", ".webp"}
MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


@dataclass(frozen=True)
class InspectionResult:
    code: str
    file_name: str
    media_type: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "file_name": self.file_name,
            "media_type": self.media_type,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }


def _signature_matches(path: Path, data: bytes) -> bool:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return data.startswith(b"%PDF-")
    if suffix == ".docx":
        return data.startswith(b"PK\x03\x04")
    if suffix == ".png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if suffix in {".jpg", ".jpeg"}:
        return data.startswith(b"\xff\xd8\xff")
    if suffix == ".webp":
        return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    return False


def inspect_source(path: str | Path) -> InspectionResult:
    """Inspect metadata and magic bytes without parsing document content."""
    source = Path(path)
    suffix = source.suffix.lower()
    safe_name = source.name
    if suffix not in SUPPORTED_EXTENSIONS:
        return InspectionResult("unsupported_template_source", safe_name)
    if source.is_symlink():
        return InspectionResult("unsafe_source_path", safe_name)
    if not source.is_file():
        return InspectionResult("template_source_missing", safe_name)
    size = source.stat().st_size
    media_type = MIME_TYPES.get(suffix) or mimetypes.guess_type(source.name)[0]
    if size > MAX_SOURCE_BYTES:
        return InspectionResult("template_source_too_large", safe_name, media_type, size)
    with source.open("rb") as stream:
        data = stream.read(64)
    if not _signature_matches(source, data):
        return InspectionResult("invalid_source_signature", safe_name, media_type, size)
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return InspectionResult("source_ready", safe_name, media_type, size, digest.hexdigest())


def inspect_source_set(paths: list[str | Path]) -> dict[str, object]:
    """Inspect a bounded, deterministic source set before any document parser runs."""
    if not isinstance(paths, list) or not paths:
        return {"code": "template_source_missing", "sources": []}
    if len(paths) > MAX_SOURCE_FILES:
        return {"code": "template_source_count_exceeded", "source_count": len(paths), "sources": []}
    ordered = sorted((Path(path) for path in paths), key=lambda item: item.name.casefold())
    names = [path.name for path in ordered]
    if len(set(names)) != len(names):
        return {"code": "duplicate_source_name", "sources": []}
    results = [inspect_source(path) for path in ordered]
    first_failure = next((result for result in results if result.code != "source_ready"), None)
    if first_failure is not None:
        return {"code": first_failure.code, "sources": [first_failure.to_dict()]}
    total = sum(int(result.size_bytes or 0) for result in results)
    if total > MAX_TOTAL_SOURCE_BYTES:
        return {"code": "template_source_set_too_large", "total_size_bytes": total, "sources": []}
    return {
        "code": "source_set_ready",
        "source_count": len(results),
        "total_size_bytes": total,
        "sources": [result.to_dict() for result in results],
    }
