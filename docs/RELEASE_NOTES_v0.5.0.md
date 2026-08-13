# v0.5.0 — User template registration

## Added

- Analyze PDF, DOCX, PNG, JPG, and WEBP manuscript examples as untrusted input.
- Generate a bounded candidate with neutral HTML/PDF preview and confidence state.
- Require explicit approval of the exact candidate ID before immutable `t0.N` registration.
- Render approved custom templates as Markdown, HTML, and PDF.
- Export custom manuscript results to a separate Desktop publication folder.

## Security

- Reject unsupported formats, invalid signatures, oversized files, raw markup, executable expressions, paths, and source copying.
- Keep source files out of candidate and release packages; retain only safe names, media types, sizes, and hashes.
- Preserve separate Vault and Desktop publication statuses.

## Compatibility

- Existing `book_a4`, `adaptive_blog`, conversation archive, exact bundle deletion, and immutable manuscript version contracts remain available.
