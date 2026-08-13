from __future__ import annotations

from pathlib import Path

import pdfplumber


def extract_pdf_evidence(path: str | Path) -> dict[str, object]:
    with pdfplumber.open(path) as pdf:
        if len(pdf.pages) > 300:
            raise ValueError("template_source_too_large")
        pages = []
        for index, page in enumerate(pdf.pages, start=1):
            pages.append({"page": index, "width": round(page.width, 3), "height": round(page.height, 3), "orientation": "landscape" if page.width >= page.height else "portrait", "table_count": len(page.find_tables())})
    return {"page_count": len(pages), "pages": pages}
