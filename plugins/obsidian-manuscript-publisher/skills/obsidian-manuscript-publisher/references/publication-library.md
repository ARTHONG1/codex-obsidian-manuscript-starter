# Verified Desktop Publication Library

The desktop publication library is a one-way, copy-ready export of one explicitly selected verified version. The Obsidian Vault remains the source of record. Editing a desktop bundle never edits the Vault or the immutable local source version.

## Natural-Language Routes

- `원고로 완성해줘`: finish the `book_a4` pipeline, then export its verified version.
- `범용 블로그형으로 만들어줘`: finish the `adaptive_blog` pipeline, then export its verified version.
- `바탕화면 출판함만 다시 만들어줘`: re-export the exact already-verified version named or established in the active request. Do not regenerate prose or images.
- `v0.3 검증본을 출판함에 정리해줘`: backfill only that explicitly named version.

For re-export or backfill, require the exact project, profile, and version. Never scan all historical versions implicitly. If any of those three values is missing or ambiguous, ask for the missing value instead of selecting a nearby folder.

## Preconditions and Pipeline Order

For either profile, use this order:

```text
validation → render → Vault publication attempt → desktop export
```

Desktop export is allowed only when the selected immutable `v0.N` package has a fresh `status: ready` validation report and all required rendered files. Recalculate the validation-input and asset hashes before export. A stale report, missing render, unexpected file, unsafe path, or hash mismatch stops before `00 최신본` changes.

Vault publication and desktop export are independent outcomes. Obsidian may be closed or Local REST may fail while a fresh local package remains eligible for desktop export. Never describe a desktop export as successful Vault publication.

## Publication Root

Read `publicationRoot` and `vaultPath` from `%LOCALAPPDATA%\CodexObsidianManuscript\runtime.json`. When a legacy schema-v1 runtime omits `publicationRoot`, resolve the Windows Desktop known folder and append `옵시디언 원고`; do not hard-code a user profile path.

The default root is:

```text
<Windows 바탕화면>\옵시디언 원고
```

The root contains `00 원고 목록.html`, `00 사용 방법.txt`, and `00 Obsidian 보관함 폴더.lnk`. The shortcut opens the configured Vault directory in File Explorer. Do not construct an `obsidian://` URL from a guessed Vault name.

## Folder Contract

The project component is the registry's exact `destination_root`, never an inferred title.

```text
옵시디언 원고\
├─ 00 원고 목록.html
├─ 00 사용 방법.txt
├─ 00 Obsidian 보관함 폴더.lnk
└─ <project destination_root>\
   ├─ 01 출판 원고형\
   │  └─ <Part>\<chapter>\
   │     ├─ 00 최신본\
   │     └─ 99 이전버전\v0.N\
   └─ 02 범용 블로그형\
      └─ <validated-slug>\
         ├─ 00 최신본\
         └─ 99 이전버전\v0.N\
```

### `book_a4` Bundle

```text
00 최신본\
├─ 01 본문-복사용.txt
├─ 02 원고.md
├─ 03 미리보기.html
├─ 04 인쇄용.pdf
├─ 05 이미지-삽입순서.md
├─ images\
│  ├─ 01-미리보기.png
│  ├─ 02-Step-01.png
│  └─ ...
└─ _meta\export-manifest.json
```

### `adaptive_blog` Bundle

```text
00 최신본\
├─ 01 본문-복사용.txt
├─ 02 블로그.md
├─ 03 미리보기.html
├─ 04 이미지-삽입순서.md
├─ images\
│  ├─ 01-대표이미지.png
│  ├─ 02-검증근거-1.png
│  └─ ...
└─ _meta\export-manifest.json
```

An `adaptive_blog` bundle has no PDF. Do not copy a nearby PDF or generate one during export.

## Beginner Copy Workflow

1. Open `00 원고 목록.html` and select the item's `00 최신본`.
2. Open `01 본문-복사용.txt`, select the text, and paste it into the destination editor. Image positions appear as explicit `[이미지 NN 삽입: ...]` markers followed by captions.
3. Open `04 이미지-삽입순서.md` for a blog or `05 이미지-삽입순서.md` for a book. Upload the matching numbered file from `images` at each marker.
4. Use `03 미리보기.html` to check order and appearance. For `book_a4`, use `04 인쇄용.pdf` only for print and page-layout review.

Markdown and HTML use rewritten relative links to the numbered `images` files. They are portable files, but the plain-text file is the primary paste source for editors that make image extraction difficult.

This feature does not post directly to Naver, Tistory, WordPress, or another external service. The user performs the final paste, image upload, platform preview, and publication check.

## Exporter CLI

Run only after the selected package passes its profile validator and renderer:

```text
scripts/export_publication_bundle.py
  --source-version-dir <absolute selected v0.N folder>
  --publication-root <absolute runtime publicationRoot>
  --project-destination-root <exact registry destination_root>
  --vault-path <absolute runtime vaultPath>
```

- `--source-version-dir` names one immutable version only.
- `--publication-root` is the configured publication root, not the Vault.
- `--project-destination-root` is copied exactly from the registered project.
- `--vault-path` is used only for boundary checks and status context; never pass REST credentials.

## Result Statuses

Successful command JSON uses one of these statuses:

| Status | Meaning |
| --- | --- |
| `exported` | The selected newer version became `00 최신본`; the former latest was preserved in history. |
| `history_exported` | The selected older version was added to `99 이전버전` without changing the newer latest. |
| `already_exported` | The same immutable bytes are already present; nothing was rewritten. |

Deterministic failures include `validation_not_ready`, `stale_validation`, `unexpected_source_file`, `unsafe_path`, `asset_hash_mismatch`, and `immutable_export_conflict`. A failure must leave the prior verified `00 최신본` readable and unchanged.

Completion reporting always includes separate fields:

```text
vault_publication_status: published | not_published | publication_failed
desktop_export_status: exported | history_exported | already_exported | export_failed
```

Also report the selected profile, source version, and final desktop path. Do not collapse the two status fields into one `completed` claim.

## Export Manifest

`_meta/export-manifest.json` contains non-secret traceability data only:

- schema version, profile, project destination root, title, and immutable source version;
- validation status and validated input hashes;
- source and exported file hashes;
- numbered-image rename map;
- Vault publication status when known;
- export timestamp and immutable bundle fingerprint.

It must not contain API keys, bearer tokens, private keys, certificate contents, Local REST configuration contents, conversation archives, private attachment paths, or arbitrary environment variables.

## Latest, History, and Recovery

- `00 최신본` is the newest successfully verified export for that item.
- `99 이전버전\v0.N` is immutable history. Never overwrite non-identical bytes for an existing version.
- An identical re-export is idempotent and returns `already_exported`.
- Different bytes presented as the same `v0.N` return `immutable_export_conflict`.
- Export builds in an exporter-owned staging directory, verifies every output hash, and promotes only the complete bundle.
- Interrupted-export recovery may inspect only exporter-owned `.staging-*` and `.previous-*` siblings under the exact item root. It must restore the last verified latest or stop for manual review; it must never recursively clean the publication root, item root, Vault, or source version.

## Security Boundaries

- Export only profile-allowlisted reader files and manifest-listed images.
- Reject traversal, absolute/UNC/drive-prefixed asset paths, reserved Windows names, trailing dots or spaces, destination escape, and source/destination overlap.
- Reject symlinks, junctions, and other reparse points in source or destination boundaries.
- Never move the Vault, write desktop edits back to it, or copy unrelated Vault notes.
- Never pass, log, document, or place a Local REST credential in an export command or bundle.

If a Local REST key was exposed, the user must manually choose `Reset all crypto` in the Obsidian plugin settings. `Re-generate certificates` alone does not rotate that key. Do not record the replacement key.
