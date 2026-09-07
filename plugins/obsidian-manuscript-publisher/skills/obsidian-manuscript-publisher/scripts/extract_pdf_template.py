from __future__ import annotations

from pathlib import Path

import pdfplumber
from pypdf import PdfReader
from template_source import MAX_SOURCE_BYTES


MAX_PAGES = 300
_FORBIDDEN_MARKERS = (
    b"/javascript",
    b"/js",
    b"/openaction",
    b"/aa",
    b"/launch",
    b"/embeddedfiles",
    b"/richmedia",
    b"/acroform",
    b"/xfa",
)


def extract_pdf_evidence(path: str | Path) -> dict[str, object]:
    source = Path(path)
    try:
        if source.stat().st_size > MAX_SOURCE_BYTES:
            raise ValueError("template_source_too_large")
        raw = source.read_bytes()
        lowered = raw.lower()
        if any(marker in lowered for marker in _FORBIDDEN_MARKERS):
            raise ValueError("unsafe_pdf_source")
        reader = PdfReader(str(source), strict=True)
        if reader.is_encrypted:
            raise ValueError("unsafe_pdf_source")
        page_count = len(reader.pages)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("invalid_pdf_source") from exc
    if page_count > MAX_PAGES:
        raise ValueError("template_source_too_large")
    with pdfplumber.open(path) as pdf:
        if len(pdf.pages) != page_count:
            raise ValueError("pdf_page_count_changed")
        if len(pdf.pages) > MAX_PAGES:
            raise ValueError("template_source_too_large")
        pages = []
        for index, page in enumerate(pdf.pages, start=1):
            pages.append({"page": index, "width": round(page.width, 3), "height": round(page.height, 3), "orientation": "landscape" if page.width >= page.height else "portrait", "table_count": len(page.find_tables())})
    return {"page_count": len(pages), "pages": pages}
