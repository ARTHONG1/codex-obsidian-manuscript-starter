---
name: obsidian-manuscript-publisher
description: Use when a user wants to register an Obsidian writing project, save or refresh the current Codex conversation, publish a platform-independent blog or a manuscript using an approved custom template, register a template candidate, delete the current conversation bundle, exclude a task, pause a project, or export a verified desktop publication bundle.
---

# Obsidian Manuscript Publisher

Use Obsidian as an auditable conversation source and editorial workspace. Work with the active Codex task and an explicitly registered project; preserve exact task/thread isolation, deterministic validation, byte-readback, and immutable versions.

## Read the Matching Workflow

- `이 프로젝트를 원고 프로젝트로 등록해줘`, `이 대화 전체를 옵시디언에 저장해줘`, `이 대화 원고 재료 최신화해줘`, `이 대화 옵시디언에 정리해줘`, `이번 작업은 저장하지 마`, or pause requests: read [references/conversation-workflow.md](references/conversation-workflow.md).
- `이 대화의 옵시디언 자료를 전부 삭제해줘` or `이 대화 옵시디언 폴더를 지워줘`: read [references/deletion-workflow.md](references/deletion-workflow.md).
- `범용 블로그형`, `블로그 버전`, or `Markdown과 HTML 블로그`: read [references/adaptive-blog-workflow.md](references/adaptive-blog-workflow.md).
- PDF, DOCX, PNG, JPG, WEBP template analysis, `출판사 A 원고형`, or custom publication: read [references/custom-manuscript-workflow.md](references/custom-manuscript-workflow.md).
- `바탕화면 출판함만 다시 만들어줘`, `v0.N 검증본을 출판함에 정리해줘`, or desktop export: read [references/publication-library.md](references/publication-library.md) and the selected profile reference.

## Output Profile Selection

The supported production profiles are `adaptive_blog` and `custom_manuscript`. There is no built-in manuscript template. For `원고를 만들어줘`, `책 원고`, or `A4 원고` without a selected template, ask which approved user template to use. If none is registered, offer to analyze a PDF, DOCX, or image sample and show a preview of the proposed template first. Do not silently select a template or turn a manuscript request into a blog.

For `둘 다`, run independent blog and custom-template pipelines after the user selects the approved custom template. Template structure, page size, and Step count come from that template. Previously created manuscripts remain the user's files; removing the built-in template does not authorize deleting or rewriting those outputs. Old built-in packages cannot be newly rendered, published, or re-exported with this version.

## Global Safety

- Read runtime configuration from `%LOCALAPPDATA%\CodexObsidianManuscript\runtime.json`; never print API keys, certificates, tokens, private records, or unrelated desktop content.
- Use only the installed HTTPS Local REST API on `127.0.0.1` for Vault writes. Do not use direct filesystem writes, `Copy-Item`, workspace fallbacks, or external image APIs.
- Require source-boundary checks for untrusted PDF, DOCX, and image input; use extractor evidence, not caller-supplied evidence.
- Require byte-for-byte readback and SHA-256 equality, deterministic validation, and immutable `v0.N`/`t0.N` allocation before reporting success.
- Never scan all Codex conversations. Never overwrite a finished version. Never call unverified output complete.
- Never delete during archive, refresh, synthesis, render, or publish. Deletion occurs only through the explicit Delete Current Conversation Bundle trigger.
- A failed publication preserves remote files and the local failed version; retry only with a fresh immutable version.

## Shared Contracts

Use the exact active task/thread ID as `conversation_key`; never infer projects or delete targets from titles or topics. Keep source JSON, material cards, manifests, validation reports, rendered outputs, and publication status tied to that exact task and selected profile. Resolve source_refs against turn IDs and attachment or file entries from the active conversation bundle; unresolved source_refs block completion. Never send a Local REST API key, certificate, or plugin configuration contents to the exporter; never send a Local REST API key in a command or report.

Archive and Refresh the Current Conversation, Synthesize an Adaptive Blog Version, User Template Registration, Synthesize a Custom Manuscript Version, Delete Current Conversation Bundle, and Exclude or Pause are on-demand Codex actions.

## Validate, Render, and Publish

Enforce the exact publication allowlist before REST. Never delete or roll back remote files automatically.

Adaptive blog versions use `02 Blog/<topic-slug>/v0.N`. Read [references/blog-schema.md](references/blog-schema.md) and [references/blog-editorial-policy.md](references/blog-editorial-policy.md); validate `blog.json` and `asset-manifest.json` with `scripts/validate_blog.py`, render `blog.md` and `blog.html` with `scripts/render_blog.py`, then publish through `scripts/publish_manuscript_version.py` using `blog-validation.json` and `publication-validation.json`. Do not create a PDF for this profile.

Custom candidates require `candidate_id`, `preview_ready`, and the exact approved candidate ID. Registration and production follow the custom workflow and its `content_contract` and `layout_contract`. Use the dedicated custom validator, renderer, and publisher; never feed custom data to the blog pipeline.

The publication order is `validation → render → Vault publication attempt → desktop export`; snapshot every allowed file before the first REST request and require byte-for-byte readback. For blogs, export using `scripts/export_publication_bundle.py` only after fresh `status: ready` validation and rendering. Custom manuscripts use `scripts/finalize_custom_publication.py` and its explicit desktop destination. A Vault REST failure does not block desktop export of an eligible local package. Report `vault_publication_status` and `desktop_export_status` separately.

Use the selected profile's deterministic errors, including `blog_profile_required`, `insufficient_evidence`, `asset_hash_mismatch`, `image_generation_failed`, `validation_not_ready`, `stale_validation`, `unexpected_source_file`, `unsafe_path`, and `immutable_export_conflict`. Stop on missing evidence, stale hashes, invalid assets, renderer errors, or incomplete readback; do not create placeholders or claim completion.

## Required AI Image Workflow and Editorial Voice

Read [references/asset-policy.md](references/asset-policy.md) and the selected profile's editorial rules. Generate relevant images with Codex's available image-generation tool, use `wide landscape composition, 16:9` where the selected layout requires it, and inspect each with `view_image`. Check purpose match, professional layout, legibility, generation artifacts, and absence of generic AI motifs. Use a numbered editorial caption immediately below each image where required by the profile; identify generated illustrations without claiming they are actual captures. `ui_screen` and `generated_scene` remain visual categories, not evidence of real execution.

Custom prose follows the approved content contract. Blog prose follows the blog editorial policy. Do not impose removed fixed Step formulas on either profile. For build-oriented topics, describe source-supported requests, creation, testing, and user checks without inventing work. Editorial prose uses `합니다` and `하기` as practical honorific forms.

## Beginner and Maintenance Notes

The installation guide documents the product-owned Python 3.12 venv, schema-v2 resume, Local REST retry, WinGet absence, six direct runtime packages, hash-locked transitive dependencies, and exact Python/Pester commands. Read [README.md](../../../../README.md), [INSTALL_PROMPT.md](../../../../INSTALL_PROMPT.md), and [docs/INSTALL_GUIDE.md](../../../../docs/INSTALL_GUIDE.md) only when installation or maintenance is requested.
