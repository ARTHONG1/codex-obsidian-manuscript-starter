from __future__ import annotations

from pathlib import Path

from docx import Document


def extract_docx_evidence(path: str | Path) -> dict[str, object]:
    document = Document(path)
    sections = [{"width": round(section.page_width / 914400, 4), "height": round(section.page_height / 914400, 4), "orientation": str(section.orientation)} for section in document.sections]
    return {"paragraph_count": len(document.paragraphs), "table_count": len(document.tables), "section_count": len(sections), "sections": sections}
