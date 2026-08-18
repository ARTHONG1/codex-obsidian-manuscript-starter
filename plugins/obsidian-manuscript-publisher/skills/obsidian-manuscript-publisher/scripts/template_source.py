"""Security-first inspection for user-supplied manuscript template examples."""

from __future__ import annotations

import hashlib
import mimetypes
import os
import shutil
import stat
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


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


class TemplateSourceError(ValueError):
    """A deterministic, path-free source security failure."""


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


@dataclass(frozen=True)
class SnapshotSource:
    safe_name: str
    media_type: str
    size_bytes: int
    sha256: str
    _path: Path

    @property
    def path(self) -> Path:
        return self._path

    def to_manifest(self) -> dict[str, object]:
        return {
            "file_name": self.safe_name,
            "media_type": self.media_type,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }


def _is_reparse_point(path: Path) -> bool:
    try:
        mode = path.lstat().st_mode
    except OSError:
        return False
    if stat.S_ISLNK(mode):
        return True
    is_junction = getattr(Path, "is_junction", None)
    if is_junction is not None:
        try:
            return bool(is_junction(path))
        except OSError:
            return True
    return False


def _source_error(code: str) -> TemplateSourceError:
    return TemplateSourceError(code)


def _identity(path: Path) -> tuple[int, int]:
    info = path.stat(follow_symlinks=False)
    return info.st_dev, info.st_ino


def _hash_file(path: Path) -> tuple[int, str]:
    size = 0
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def _validate_staging_parent(staging_parent: str | Path | None) -> tuple[Path, tuple[int, int]] | None:
    if staging_parent is None:
        return None
    parent = Path(staging_parent)
    if not parent.is_dir() or _is_reparse_point(parent):
        raise _source_error("unsafe_staging_parent")
    try:
        return parent, _identity(parent)
    except OSError:
        raise _source_error("unsafe_staging_parent") from None


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
    if _is_reparse_point(source):
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
    if len({name.casefold() for name in names}) != len(names):
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


def _remove_exact_owned_snapshot(
    owned: Path,
    staging_parent: Path,
    expected_parent_identity: tuple[int, int],
    expected_owned_identity: tuple[int, int],
) -> None:
    if (
        not owned.name.startswith("codex-template-snapshot-")
        or owned.parent != staging_parent
        or _is_reparse_point(owned)
        or not owned.is_dir()
    ):
        return
    try:
        parent_identity = _identity(staging_parent)
        owned_identity = _identity(owned)
    except OSError:
        return
    if parent_identity != expected_parent_identity:
        return
    if owned_identity != expected_owned_identity:
        return
    try:
        shutil.rmtree(owned)
    except OSError:
        raise _source_error("snapshot_filesystem_error") from None


def _validate_source_boundary(source: Path, expected_size: int) -> tuple[int, int]:
    if _is_reparse_point(source) or not source.is_file():
        raise _source_error("source_changed_during_snapshot")
    try:
        identity = _identity(source)
        if source.stat().st_size != expected_size:
            raise _source_error("source_changed_during_snapshot")
        return identity
    except OSError:
        raise _source_error("source_changed_during_snapshot") from None


def _copy_and_verify_sources(
    paths: list[str | Path],
    inspected: list[dict[str, object]],
    owned: Path,
) -> list[SnapshotSource]:
    ordered = sorted((Path(path) for path in paths), key=lambda item: item.name.casefold())
    snapshots = []
    for source, manifest in zip(ordered, inspected):
        expected_size = int(manifest["size_bytes"])
        expected_sha256 = str(manifest["sha256"])
        destination = owned / source.name
        copied_size = 0
        copied_digest = hashlib.sha256()
        source_identity = _validate_source_boundary(source, expected_size)
        try:
            with source.open("rb") as source_stream, destination.open("wb") as destination_stream:
                if _is_reparse_point(source) or _identity(source) != source_identity:
                    raise _source_error("source_changed_during_snapshot")
                for chunk in iter(lambda: source_stream.read(1024 * 1024), b""):
                    destination_stream.write(chunk)
                    copied_size += len(chunk)
                    copied_digest.update(chunk)
        except TemplateSourceError:
            raise
        except (OSError, ValueError):
            raise _source_error("source_changed_during_snapshot")
        if copied_size != expected_size or copied_digest.hexdigest() != expected_sha256:
            raise _source_error("source_changed_during_snapshot")
        try:
            staged_size, staged_sha256 = _hash_file(destination)
        except (OSError, ValueError):
            raise _source_error("snapshot_filesystem_error") from None
        if staged_size != expected_size or staged_sha256 != expected_sha256:
            raise _source_error("source_changed_during_snapshot")
        _validate_source_boundary(source, expected_size)
        try:
            current_size, current_sha256 = _hash_file(source)
        except (OSError, ValueError):
            raise _source_error("snapshot_filesystem_error") from None
        if current_size != expected_size or current_sha256 != expected_sha256:
            raise _source_error("source_changed_during_snapshot")
        snapshots.append(
            SnapshotSource(
                safe_name=str(manifest["file_name"]),
                media_type=str(manifest["media_type"]),
                size_bytes=expected_size,
                sha256=expected_sha256,
                _path=destination,
            )
        )
    return snapshots


@contextmanager
def snapshot_source_set(
    paths: list[str | Path],
    staging_parent: str | Path | None = None,
) -> Iterator[tuple[SnapshotSource, ...]]:
    inspection = inspect_source_set(paths)
    if inspection["code"] != "source_set_ready":
        raise _source_error(str(inspection["code"]))
    validated_parent = _validate_staging_parent(staging_parent)
    parent = validated_parent[0] if validated_parent else None
    cleanup_parent = parent or Path(tempfile.gettempdir())
    try:
        cleanup_parent_identity = validated_parent[1] if validated_parent else _identity(cleanup_parent)
        owned = Path(tempfile.mkdtemp(prefix="codex-template-snapshot-", dir=parent))
        owned_identity = _identity(owned)
    except OSError:
        raise _source_error("snapshot_filesystem_error") from None
    try:
        snapshots = _copy_and_verify_sources(paths, inspection["sources"], owned)
        yield tuple(snapshots)
    finally:
        _remove_exact_owned_snapshot(owned, cleanup_parent, cleanup_parent_identity, owned_identity)
