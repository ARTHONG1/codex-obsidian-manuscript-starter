# Custom Manuscript Workflow

Use this reference for PDF, DOCX, PNG, JPG, WEBP analysis and approved custom-template production.

Treat every source as untrusted input. Run the canonical source boundary before parsing; enforce count, size, page, pixel, ZIP, path, macro, relationship, embedded-file, and image-format limits. Extract bounded evidence only; caller-supplied evidence never replaces extractor output.

The first analysis request creates a local candidate with a canonical source manifest, bounded observations, declaration-only template, `candidate_id`, `preview.html`, `preview.pdf`, confidence, and unresolved items. Show the preview and stop. Registration requires `preview_ready` plus the exact approved candidate ID, allocates immutable `t0.N`, and publishes through HTTPS Local REST with byte readback.

Production consumes the approved immutable snapshot and one immutable `LayoutPlan`. Markdown, HTML, and PDF use the same ordered blocks. Missing fonts, renderer errors, stale hashes, empty PDFs, invalid evidence, or incomplete publication are hard failures; never write a Vault template through filesystem fallback or return a placeholder.
