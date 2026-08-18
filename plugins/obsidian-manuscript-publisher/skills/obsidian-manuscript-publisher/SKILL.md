---
name: obsidian-manuscript-publisher
description: Use when a user wants to register an Obsidian writing project, save or refresh the current Codex conversation, synthesize and publish an A4 manuscript or platform-independent blog, create a custom-template candidate, delete the current conversation bundle, exclude one task, pause a project, or export a verified desktop publication bundle.
---

# Obsidian Manuscript Publisher

Use Obsidian as an auditable conversation source and editorial workspace. Work only with the active Codex task and an explicitly registered project; preserve exact task/thread isolation, deterministic validation, byte-readback, and immutable versions.

## Read the Matching Workflow

- `이 프로젝트를 원고 프로젝트로 등록해줘`, `이 대화 전체를 옵시디언에 저장해줘`, `이 대화 원고 재료 최신화해줘`, `이 대화 옵시디언에 정리해줘`, `이번 작업은 저장하지 마`, or pause requests: read [references/conversation-workflow.md](references/conversation-workflow.md).
- `이 대화의 옵시디언 자료를 전부 삭제해줘` or `이 대화 옵시디언 폴더를 지워줘`: read [references/deletion-workflow.md](references/deletion-workflow.md).
- `출판 원고형`, `A4 원고`, `책 원고`, `원고를 만들어줘`, `Part 1-01 원고로 합성해줘`, or `실제 결과물을 만들고 이미지 포함 원고로 완성해줘`: read [references/book-a4-workflow.md](references/book-a4-workflow.md) and [references/master-editorial-profile.md](references/master-editorial-profile.md).
- `범용 블로그형`, `블로그 버전`, `Markdown과 HTML 블로그`, or `둘 다`: read [references/adaptive-blog-workflow.md](references/adaptive-blog-workflow.md).
- PDF, DOCX, PNG, JPG, WEBP analysis, approved user-template production, `출판사 A 원고형`, or custom publication: read [references/custom-manuscript-workflow.md](references/custom-manuscript-workflow.md).
- `기존 양식`, `레거시 양식`, explicit `V1`, explicit `V2`, or immutable historical V1/V2 work: read [references/legacy-book-contracts.md](references/legacy-book-contracts.md).
- `바탕화면 출판함만 다시 만들어줘`, `v0.N 검증본을 출판함에 정리해줘`, or desktop export: read [references/publication-library.md](references/publication-library.md) and the selected profile reference.

## Global Routing

Output Profile Selection: choose one profile before synthesis. `book_a4` is the default for a manuscript request that names no profile; `book_a4 remains the default` for backward compatibility. New A4 and blog synthesis use the V3 editorial profile; declare `template_version: 3` for new A4 packages and read the master profile before creating content or visuals.

Explicit historical V1/V2 requests and immutable historical versions load only [references/legacy-book-contracts.md](references/legacy-book-contracts.md). Never let legacy wording override a new/default request. Run `scripts/select_book_template.py` before new A4 images or publication; explicit version selection wins and unknown versions stop.

Keep `book_a4`, `adaptive_blog`, and `custom_manuscript` outputs isolated. Never send `blog.json` to a book validator or `manuscript.json` to a blog validator. For `둘 다`, run two independent immutable pipelines. Continue only when validation reports `status: ready`; render before desktop export.

## Global Safety

- Read runtime configuration from `%LOCALAPPDATA%\CodexObsidianManuscript\runtime.json`; never print API keys, certificates, tokens, private records, or unrelated desktop content.
- Use only the installed HTTPS Local REST API on `127.0.0.1` for Vault writes. Do not use direct filesystem writes, `Copy-Item`, workspace fallbacks, or external image APIs.
- Require source-boundary checks for untrusted PDF, DOCX, and image input; use extractor evidence, not caller-supplied evidence.
- Require byte-for-byte readback and SHA-256 equality, deterministic validation, and immutable `v0.N`/`t0.N` allocation before reporting success.
- Never scan all Codex conversations. Never overwrite a finished version. Never call unverified output complete.
- Never delete during archive, refresh, synthesis, render, or publish. Deletion occurs only through the explicit Delete Current Conversation Bundle trigger.
- A failed publication preserves remote files and the local failed version; retry only with a fresh immutable version.

## Shared Contracts

Use the exact active task/thread ID as `conversation_key`; never infer projects or delete targets from titles or topics. Keep source JSON, material cards, manifests, validation reports, rendered outputs, and publication status tied to that exact task and selected profile. Never send a Local REST API key, certificate, or plugin configuration contents to the exporter; report `vault_publication_status` and `desktop_export_status` separately. Lowercase safety wording remains explicit: never send a Local REST API key.

Archive and Refresh the Current Conversation, Synthesize a Manuscript Version, Synthesize an Adaptive Blog Version, Output Profile Selection, User Template Registration, New Book A4 Routing Contract, Flexible Build-Step Contract, Required AI Image Workflow, Validate, Render, and Publish, Delete Current Conversation Bundle, Editorial Voice, Exclude or Pause, and Safety remain the public contract names. This is an on-demand Codex action.

The flexible build-step contract requires real creation, modification, integration, testing, or correction evidence. Every Step has `user_request`, `codex_action`, and `user_check`, uses the exact noun allowlist, and shows the user's request, Codex's concrete action/result, and the user's observable check; do not invent build work or present completed-tool usage as a build Step.

Shared implementation anchors are `manuscript.json`, `asset-manifest.json`, `asset-validation.json`, `blog.json`, `blog-validation.json`, `publication-validation.json`, `production-plan.json`, `validate_manuscript.py`, `render_manuscript.py`, `validate_blog.py`, `render_blog.py`, `publish_manuscript_version.py`, `scripts/export_publication_bundle.py`, `status: ready`, `v0.N`, `active conversation bundle`, `turn IDs and attachment or file entries`, and `unresolved source_refs`. The exact noun allowlist is `준비`, `분석`, `설계`, `구성`, `구현`, `연결`, `설정`, `생성`, `검증`, `수정`, `테스트`, `설치`, `배포`, `실행`, `적용`, `활용`.

The publication order is `validation → render → Vault publication attempt → desktop export`; snapshot every allowed file before the first REST request, require byte-for-byte readback, preserve failed remote files, and retry only with a fresh immutable version. The complete deterministic contract includes `blog_profile_required`, `insufficient_evidence`, `asset_hash_mismatch`, `image_generation_failed`, `validation_not_ready`, `stale_validation`, `unexpected_source_file`, `unsafe_path`, and `immutable_export_conflict`.

New V3 Step bodies contain 2-4 sentences; sufficiently detailed tips contain 3-5 sentences. Use `wide landscape composition, 16:9`, `view_image`, `numbered editorial caption`, `ui_screen`, and `generated_scene`; review purpose match, professional layout, legibility, generation artifacts, and generic AI motifs. Read `references/blog-schema.md`, `references/blog-editorial-policy.md`, `references/manuscript-schema.md`, `references/asset-policy.md`, `references/publication-library.md`, and `references/master-editorial-profile.md` as needed. Do not load the A4 Step structure into the adaptive blog branch; do not create a PDF for that profile.

Custom candidates require `candidate_id`, `preview_ready`, and the exact approved candidate ID. Adaptive blog versions use `02 Blog/<topic-slug>/v0.N`. A Vault REST failure does not block desktop export when the local package is freshly validated and fully rendered. Editorial prose uses `합니다` and `하기` as practical honorific forms.

The exact publication allowlist is enforced before REST. Build-step interaction fields are `"user_request"`, `"codex_action"`, and `"user_check"`. A new V3 draft is invalid without `editorial_quality_version: 3`, `practice_blocks`, and `editorial_review`; a missing Korean font, stale hash, or empty PDF is a hard failure.

Adaptive blog rendering produces `blog.md` and `blog.html` only. Do not create a PDF for this profile. Never delete or roll back remote files automatically. Visual review includes absence of generic AI motifs.

Use the deterministic error codes documented by the selected profile references. Stop on missing evidence, stale hashes, unsafe paths, invalid assets, renderer errors, or incomplete readback; do not create placeholders or claim completion.

## Beginner and Maintenance Notes

The installation guide documents the product-owned Python 3.12 venv, schema-v2 resume, Local REST retry, WinGet absence, six direct runtime packages, hash-locked transitive dependencies, and exact Python/Pester commands. Read [README.md](../../../../README.md), [INSTALL_PROMPT.md](../../../../INSTALL_PROMPT.md), and [docs/INSTALL_GUIDE.md](../../../../docs/INSTALL_GUIDE.md) only when installation or maintenance is requested.
