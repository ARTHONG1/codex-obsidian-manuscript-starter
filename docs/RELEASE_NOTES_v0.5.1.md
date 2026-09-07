# v0.5.1

## Security and custom-template recovery

- Pins the document runtime to Python 3.12.x with Pillow 12.3.0, ReportLab 4.4.3, python-docx 1.2.0, pdfplumber 0.11.9, pypdfium2 5.12.1, and pypdf 5.9.0.
- Rejects unsafe PDF, DOCX, and image inputs before extraction.
- Binds template registration to an immutable candidate hash and exact approval.
- Registers custom templates through HTTPS Local REST with byte readback; filesystem Vault fallback is not supported.
- Uses one declarative LayoutPlan for custom Markdown, HTML, and PDF output.
- Keeps v0.5.0 immutable and does not move or overwrite its tag.

This release does not include user Vault files, API keys, certificates, source documents, or generated publication output.
