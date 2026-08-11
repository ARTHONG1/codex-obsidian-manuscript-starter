# Desktop Verified Manuscript Publication Library Design

## Goal

Create a desktop folder named `옵시디언 원고` that presents every verified manuscript or blog as an easy-to-find publication bundle. The existing Obsidian Vault remains in place and remains the source of record; the desktop folder is a one-way, derived export intended for copying text, uploading images, previewing layout, and sending files to an editor.

## Scope

This feature exports two existing output profiles:

- `book_a4`: copy-ready text, Markdown, HTML, PDF, insertion guide, and numbered images.
- `adaptive_blog`: copy-ready text, Markdown, HTML, insertion guide, and numbered images. It never creates a blog PDF.

It also creates a root index and a shortcut to the configured Vault folder. It does not move the Vault, scan unrelated Codex tasks, publish to a web platform, create a DOCX file, or alter an immutable source version.

## Source and Destination Boundary

The configured Vault remains at the path recorded in `%LOCALAPPDATA%\CodexObsidianManuscript\runtime.json`. A typical installation points to `%USERPROFILE%\Documents\Codex-Wiki`, but implementation must read configuration rather than hard-code this path.

The export root is resolved with the Windows Known Folder API and defaults to:

```text
<Windows Desktop>\옵시디언 원고
```

The export script accepts an explicit destination for tests and advanced use. It must reject a destination that resolves to a filesystem root, the user profile root, the Vault root, the source version itself, or a path outside the explicitly selected publication root.

## Desktop Information Architecture

```text
옵시디언 원고\
├─ 00 원고 목록.html
├─ 00 사용 방법.txt
├─ 00 Obsidian 보관함 폴더.lnk
└─ AAA AI Agent Automation\
   ├─ 01 출판 원고형\
   │  └─ Part 1\
   │     └─ 03 카카오 경제 리포트 자동화\
   │        ├─ 00 최신본\
   │        │  ├─ 01 본문-복사용.txt
   │        │  ├─ 02 원고.md
   │        │  ├─ 03 미리보기.html
   │        │  ├─ 04 인쇄용.pdf
   │        │  ├─ 05 이미지-삽입순서.md
   │        │  ├─ images\
   │        │  │  ├─ 01-미리보기.png
   │        │  │  ├─ 02-Step-01.png
   │        │  │  └─ 03-실전-활용.png
   │        │  └─ _meta\export-manifest.json
   │        └─ 99 이전버전\
   │           ├─ v0.1\
   │           └─ v0.2\
   └─ 02 범용 블로그형\
      └─ evidence-based-blog-workflow\
         ├─ 00 최신본\
         │  ├─ 01 본문-복사용.txt
         │  ├─ 02 블로그.md
         │  ├─ 03 미리보기.html
         │  ├─ 04 이미지-삽입순서.md
         │  ├─ images\
         │  │  ├─ 01-대표이미지.png
         │  │  └─ 02-검증흐름.png
         │  └─ _meta\export-manifest.json
         └─ 99 이전버전\
            └─ v0.1\
```

The project folder uses the registry `destination_root`, not an inferred title. A book item uses `manuscript.json.part`, `chapter`, and `title`. A blog item uses the validated lowercase ASCII `slug`. Visible folder components are sanitized for Windows and retain a stable suffix when sanitization creates a collision.

## Copy-Ready Bundle Contract

### `01 본문-복사용.txt`

This is the default file for copying into a blog editor, word processor, or publisher form. It contains plain text, not Markdown image syntax or HTML. Every image position becomes an explicit marker such as:

```text
[이미지 02 삽입: 생성 결과 검증과 오류 수정]
캡션: 그림 1-03-2. 검증 결과와 수정 지점
```

Book text follows the fixed manuscript editorial order. Blog text follows the rendered article order. Paragraph boundaries remain intact.

### `02 원고.md` or `02 블로그.md`

The validated Markdown is copied and its image links are rewritten to the numbered files under `images/`. It remains portable and opens correctly inside the desktop bundle.

### `03 미리보기.html`

The validated HTML is copied and exact version-local image references are rewritten to the same numbered files. The exporter does not interpret or execute arbitrary HTML; it rewrites only manifest-listed image paths. The result must work offline and contain no added scripts or tracking.

### `04 인쇄용.pdf`

This exists only for `book_a4` and is copied byte-for-byte from the verified render. It is for layout review and printing, not for extracting text or images.

### `04/05 이미지-삽입순서.md`

The insertion guide contains a table with sequence number, numbered filename, insertion location, caption, alternative text, source `asset_id`, source filename, and SHA-256. The order is deterministic:

- `book_a4`: preview, Step 1 through Step N, real-world use.
- `adaptive_blog`: hero, then section visuals in article order.

### `_meta\export-manifest.json`

The manifest contains only non-secret traceability data:

- schema version;
- output profile;
- project destination root;
- source immutable version (`v0.N`);
- source file hashes;
- validation status and validation-input hashes;
- exported file paths and hashes;
- image rename map;
- Vault publication status when known;
- export timestamp.

It never stores an API key, certificate path contents, conversation text, private attachment paths, or arbitrary environment variables.

## Validation Gate

Desktop export runs only after deterministic validation and rendering.

For `book_a4`, all of the following are required:

1. `manuscript.json.output_profile` is `book_a4`.
2. `asset-validation.json.status` is `ready`.
3. Current `manuscript.json` and `asset-manifest.json` SHA-256 values equal `validated_inputs`.
4. The exact source Markdown, `manuscript.html`, and `manuscript.pdf` exist.
5. Every referenced image is version-local, manifest-listed, and hash-valid.
6. No unexpected publication file is copied.

For `adaptive_blog`, all of the following are required:

1. `blog.json.output_profile` is `adaptive_blog`.
2. `blog-validation.json.status` is `ready`.
3. Current `blog.json` and `asset-manifest.json` SHA-256 values equal `validated_inputs`.
4. `blog.md` and `blog.html` exist.
5. Every referenced image is version-local, manifest-listed, and hash-valid.
6. No PDF is created or copied.

Vault publication and desktop export are separate results. If Obsidian is closed, a fully validated local package may still be exported, while `_meta\export-manifest.json` records Vault publication as `not_published` or `publication_failed`. The completion message must not confuse verified desktop export with successful Vault publication.

## Export Transaction and Version Handling

The source version is immutable. Export uses these steps:

1. Resolve and validate the exact source package, project, profile, destination, and version.
2. Build the complete bundle in a sibling staging directory under the selected item root.
3. Rewrite only exact manifest-listed image references.
4. Hash every staged output and write `export-manifest.json` last.
5. Read back every staged file and verify its hash.
6. If the same source version and identical hashes already exist, return `already_exported` without rewriting.
7. If the same source version exists with different bytes, stop with `immutable_export_conflict`.
8. Preserve the current `00 최신본` until the new staging bundle is complete.
9. Swap the verified staging bundle into `00 최신본`; archive the former latest under `99 이전버전\<source-version>`.
10. Update the root index only after the item swap succeeds.

Recovery recognizes interrupted `.staging-*` and `.previous-*` directories inside the exact item root. It restores the last verified latest or removes only its own verified-empty staging directory. It never recursively deletes a computed path outside the selected publication item.

## Index and Shortcuts

`00 원고 목록.html` is a static offline index regenerated atomically after successful exports. It groups entries by project and profile and displays title, source version, validation state, Vault publication state, export time, and links to copy text, preview, PDF when present, and the item folder. It contains no JavaScript and no tracking.

`00 사용 방법.txt` explains the three-step workflow: copy `01 본문-복사용.txt`, upload numbered images according to the insertion guide, then use HTML/PDF only for preview.

`00 Obsidian 보관함 폴더.lnk` opens the exact configured Vault directory in File Explorer. The design deliberately avoids a guessed `obsidian://open?vault=...` URL because an unregistered or renamed Vault produces `Vault not found`.

## Integration with the Existing Skill

Add one deterministic exporter script to the skill and invoke it after a profile validates and renders. The natural-language behavior becomes:

- `원고로 완성해줘`: validate, render, publish to Vault when available, then export the verified desktop bundle.
- `범용 블로그형으로 만들어줘`: validate, render, publish to Vault when available, then export the verified desktop bundle.
- `바탕화면 출판함만 다시 만들어줘`: re-export the exact named verified version without regenerating manuscript content or images.
- `기존 검증본도 출판함에 정리해줘`: backfill only explicitly selected versions; never scan and export every historical folder implicitly.

The export destination may be recorded as a non-secret `publicationRoot` path in runtime configuration. Existing configurations without that field resolve the Windows Desktop default at runtime and remain valid.

## Security and Privacy

- Copy only exact allowlisted reader-facing outputs and manifest-listed images.
- Reject source or destination symlinks, junctions, and reparse points.
- Reject absolute image paths, traversal segments, drive prefixes, UNC paths, reserved Windows names, and trailing dot/space aliases.
- Never read or copy Local REST bearer tokens, private keys, certificates, unrelated Vault notes, conversation bundles, or unselected attachments.
- Do not overwrite or delete an immutable source version.
- Keep the last verified desktop latest intact on every failure before the final swap.
- Log paths relative to the publication root where possible; do not emit secrets.

## Initial Rollout

The first implementation creates the desktop root and exports only the currently selected verified package. It does not bulk-copy old Vault content. A separate explicit backfill request may export named historical versions after the base workflow is proven.

The current `adaptive-blog-verification-v0.1` fixture is suitable for a smoke export because its validation report is `ready` and its two images are hash-valid landscape assets.

## Test and Acceptance Contract

Automated tests must prove:

1. A valid `book_a4` package produces text, Markdown, HTML, PDF, insertion guide, numbered images, and a traceability manifest.
2. A valid `adaptive_blog` package produces text, Markdown, HTML, insertion guide, numbered images, and no PDF.
3. Image order follows the profile's editorial order and every rewritten link resolves.
4. Stale validation, missing files, hash mismatch, unexpected paths, traversal, reparse points, and malformed metadata fail before the visible latest changes.
5. A simulated failure at each transaction boundary leaves the prior `00 최신본` readable and hash-identical.
6. Re-exporting identical bytes is idempotent; conflicting bytes for the same immutable version are rejected.
7. Windows-invalid names are sanitized deterministically without collisions.
8. The root index contains correct local links and is updated only after a successful item export.
9. No API key, certificate, private key, Local REST configuration, conversation archive, or arbitrary adjacent file enters the desktop bundle.
10. Existing `book_a4`, `adaptive_blog`, publication-security, installer, and secret-scan tests remain green.

Manual acceptance on the user's machine requires:

- the folder appears at `<Desktop>\옵시디언 원고`;
- the current verified blog can be opened through `03 미리보기.html`;
- `01 본문-복사용.txt` can be pasted without Markdown image syntax;
- numbered images can be matched unambiguously using the insertion guide;
- the Vault-folder shortcut opens the exact Vault path from runtime configuration;
- an induced export failure does not damage the previous latest bundle.

## Non-Goals for Version 1

- Automatic posting to Naver, Tistory, WordPress, or another external service.
- DOCX generation.
- Moving or renaming the Obsidian Vault.
- Background timers or scheduled synchronization.
- Exporting all old versions without explicit selection.
- Editing files inside the desktop bundle and syncing those edits back into Obsidian.
