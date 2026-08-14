---
name: obsidian-manuscript-publisher
description: Use when a user wants to register an Obsidian writing project, save or refresh the current Codex conversation, synthesize and publish an A4 manuscript or a platform-independent blog, remove the current conversation's Obsidian bundle, exclude one task, or pause a writing project.
---

# Obsidian Manuscript Publisher

Use Obsidian as both an auditable conversation source and an editorial writing workspace. Keep every Codex conversation isolated by its exact task/thread ID, produce either the fixed A4 book profile or the independent adaptive blog profile, and never report success before deterministic validation passes.

## Runtime Configuration

- Read the user-local runtime configuration from `%LOCALAPPDATA%\CodexObsidianManuscript\runtime.json`. It stores the selected Vault path, the Local REST plugin configuration path, and an optional non-secret `publicationRoot`; it never stores or prints an API key.
- Resolve the Vault, registry, unit template, and Local REST configuration from that file. The registry is `<Vault>\_system\manuscript-projects.json`, the unit template is `<Vault>\02 Templates\원고 단위 템플릿.md`, and the conversation root inside each registered project is `00 Conversations/<conversation_key>`.
- Resolve the desktop publication destination from `publicationRoot`. For a compatible schema-v1 runtime that omits it, use the Windows Desktop known folder plus `옵시디언 원고`; never hard-code a user profile path.
- If the runtime configuration is missing, malformed, or points outside the configured Vault, do not guess paths and do not write directly to disk. Tell the user to run `bootstrap\install-windows.ps1` from the published starter repository, then `bootstrap\doctor.ps1` with Obsidian open.

## Non-Negotiable Contracts

1. Work only with the active Codex task and an explicitly registered manuscript project. Never infer a project from title or topic keywords and never scan unrelated tasks.
2. Use the active task/thread ID as `conversation_key`. Different IDs always produce different folders, even when titles and topics match.
3. Save Vault content only through the installed local Obsidian REST API on `127.0.0.1`. Do not use direct filesystem writes, `Copy-Item`, or delayed workspace fallbacks for Vault publication.
4. Require byte-for-byte readback for text and binary uploads. Require SHA-256 equality when publishing a manuscript version.
5. Keep every book and blog version immutable. Allocate a new `v0.N`; never overwrite an earlier draft.
6. For a newly synthesized `book_a4`, always select `template_version: 3`. Keep Step count dynamic and use Step 1 through Step N according to the actual verified build workflow.
7. New `book_a4` visuals use `generated_scene only`, created with Codex built-in image generation. V3 requires topic-specific preview, preparation, and Step visuals; an evidence-backed real-world-use visual remains optional.
8. Do not render or publish either profile while any required evidence or image is absent, invalid, duplicated, unrelated, or unverified.

## Output Profile Selection

Choose one explicit output profile before synthesis. Conversation archive, deletion, Local REST publication, byte readback, and immutable versions are shared; schemas, renderers, output files, image rules, and Vault destinations are not shared.

- `book_a4`: select for `출판 원고형`, `A4 원고`, `책 원고`, or a manuscript request that names no profile. `book_a4 remains the default` for backward compatibility.
- `adaptive_blog`: select for `범용 블로그형`, `블로그 버전`, `Markdown과 HTML 블로그`, or another explicit request for a platform-independent blog.
- `custom_manuscript`: select only when the user names an approved user template, such as `출판사 A 원고형`. A request to analyze a PDF, DOCX, or image creates a candidate preview and pauses for explicit approval; it never registers a template on the first request.

### Custom template safety contract

For `custom_manuscript`, use the canonical source-analysis pipeline. Treat PDF, DOCX, and image examples as untrusted input. The pipeline enforces the source count/size/page/pixel/ZIP limits, rejects unsafe actions, macros, external relationships, embedded files, non-allowlisted image formats, and path escapes before parsing. Do not accept caller-supplied evidence as a replacement for extractor output.

Candidate identity includes the canonical source manifest, bounded extractor evidence, bounded observations, declaration-only template, and preview content. Store only the non-secret candidate state locally per conversation. Show the candidate ID, preview, confidence, and unresolved items, then stop. Registration requires `preview_ready` plus an exact matching approved candidate ID and uses HTTPS Local REST with byte readback. Never write a Vault template with `Path.write_text`, `Copy-Item`, or another filesystem fallback.

Custom production consumes the approved immutable template snapshot and one immutable `LayoutPlan`. Markdown, HTML, and PDF must use the same ordered blocks. A missing Korean font, renderer error, stale hash, or empty PDF is a hard failure; do not return a placeholder or success state.
- `둘 다`: run `book_a4` and `adaptive_blog` as two independent pipelines and allocate a separate immutable version for each. A failure in one pipeline must not overwrite, relabel, or invalidate the other pipeline's verified output.

Always record the chosen profile in its source JSON. Never send `blog.json` to the book validator or renderer, and never send `manuscript.json` to the blog validator or renderer.

## User Template Registration

Trigger: `이 PDF를 분석해서 ‘출판사 A 원고형’ 템플릿 후보를 만들어줘` or equivalent.

1. Treat PDF, DOCX, PNG, JPG, and WEBP as untrusted input and run the source boundary before parsing.
2. Extract bounded structure evidence and create a local candidate with a `candidate_id`, `preview.html`, `preview.pdf`, confidence, and unresolved decisions.
3. Show the preview and stop. `needs_review` may preview only; registration requires `preview_ready`.
4. Register only after the user approves the exact active candidate ID. Allocate immutable `t0.N` and never overwrite an earlier template.
5. To use it, request `이 대화 재료로 ‘출판사 A 원고형’ 원고를 만들어줘`. Produce isolated custom Markdown, HTML, PDF, Vault, and Desktop outputs without changing `book_a4` or `adaptive_blog`.

## New Book A4 Routing Contract

The public profile remains `book_a4`, but the template version is a separate mandatory decision. Every newly synthesized A4 manuscript MUST use `template_version: 3`; generic requests such as `원고를 만들어줘`, `A4 원고로 합성해줘`, and `다음 버전을 만들어줘` must never silently fall back to V1 or V2.

Use V1 only when the user explicitly requests `기존 양식`, `레거시 양식`, or `V1`, or when opening, validating, rendering, or exporting an existing historical manuscript that has no `template_version: 2`. Do not rewrite a historical package merely to add the field. Report immutable manuscript version and template version separately, for example `version: v0.3`, `template: book_a4 V2`.

Before generating any image or publishing any file, run the deterministic routing/preflight helper:

```text
python scripts/select_book_template.py --request-text "<user request>"
```

The helper must return V3 for a new generic request and reject unknown template versions. A new V3 draft is invalid if it lacks `editorial_quality_version: 3`, `practice_blocks`, or `editorial_review`. Stop with `book_template_contract_mismatch`; never continue by producing a V1-looking package.

## Register a Project

Trigger: `이 프로젝트를 원고 프로젝트로 등록해줘` or equivalent.

1. Identify the exact Codex project, book, Part, chapter, template, and Vault-relative project folder.
2. Add or update only that project entry in the registry.
3. Create the project brief, `00 Conversations`, `01 Manuscript`, and `02 Blog` locations through the local REST API when absent.
4. Report the registered source project and destination. Do not change other registry entries.

## Archive and Refresh the Current Conversation

Triggers include `이 대화 전체를 옵시디언에 저장해줘`, `이 대화 원고 재료 최신화해줘`, and `이 대화 옵시디언에 정리해줘`.

1. Confirm the active task belongs to a registered project.
2. Use `codex_app__read_thread` or the active Codex thread-reading capability, include readable outputs, and follow cursors until no older turn remains. Never scan other Codex threads.
3. Normalize user, assistant, and readable tool-output turns with stable turn IDs.
4. Run `scripts/archive_conversation.py` against a staging `00 Conversations` root. The archive command creates the conversation source bundle; create `material-card.md` separately with `refresh_material_card()` after editorial material has been prepared. The bundle layout is:

```text
00 Conversations/<conversation_key>/
├─ conversation.md
├─ material-card.md
├─ metadata.json
└─ assets/
```

For a local staging archive, run the script with a UTF-8 JSON array of turn objects. The command writes no Vault files and prints the archive result as one JSON object:

```text
python scripts/archive_conversation.py \
  --conversations-root "<staging 00 Conversations>" \
  --conversation-key "<active task ID>" \
  --title "<conversation title>" \
  --turns-json "<UTF-8 turns.json>"
```

The JSON input must be an array whose objects contain `id`, `role`, and optional `text`; this local command prepares the bundle only. Use `publish_bundle` from the Python library for the separate Local REST publication step after the active task and registered project have been confirmed.

5. `conversation.md` preserves the full chronological source. `material-card.md` distills claims, candidate prose, reader problems, build-step candidates, school uses, reusable prompts/configuration, cautions, and useful assets.
6. Copy relevant conversation attachments into the same bundle's `assets/`, record hashes in `metadata.json`, and never merge assets across conversation keys.
7. Run `publish_bundle` from `scripts/archive_conversation.py` to publish every bundle file through `save_via_obsidian_rest.py` and read it back. Report `archived` and `materials_refreshed` only after every changed file verifies.
8. If the bundle was previously deleted, rebuild from all turns in the active task. Do not reuse a deleted cursor or staged fallback.
9. If thread reading, attachment handling, REST publication, or verification fails, preserve the last verified Vault state and report `failed` with the exact intended destination.

This is an on-demand Codex action. Do not create a timer, scheduled task, or background sync.

## Flexible Build-Step Contract

Apply this contract whenever synthesizing or revising `[실습하기]`.

1. Silently identify what technology was actually made: Skill, plugin, AI Agent, automation, web app, data pipeline, document generator, or another concrete tool.
2. Find the real points where a file, code module, configuration, connection, function, test result, or correction was created or changed.
3. Select those points as Step 1 through Step N. Requirements, architecture, implementation, integration, testing, correction, and packaging are examples, not a fixed sequence.
4. Name the chapter after the technology the reader will make with Codex, rather than after using an already completed service.
5. Every Step must contain:

```json
{
  "step_kind": "build",
  "build_action": "concrete creation, modification, integration, test, or correction",
  "artifact": {
    "kind": "file, code, configuration, feature, or test_result",
    "name": "observable artifact name",
    "paths": ["verified/relative/path"],
    "status": "verified"
  },
  "completion_check": "observable condition that proves the Step finished",
  "interaction": {
    "user_request": "the user's concrete request to Codex",
    "codex_action": "what Codex created, changed, connected, tested, or corrected",
    "user_check": "what the user verifies or asks Codex to revise"
  }
}
```

6. A Step that only opens, selects, sends, views, or uses an already completed tool is invalid. Put operational use in `[실전 활용하기]` instead.
7. Do not invent build work from thin source material. When the user requests result-first production, create, run, test, and correct the in-scope deliverables before writing Steps. Otherwise stop and identify the missing build evidence.
8. Render every Step as one natural paragraph of two or three sentences in this order: the user's request to Codex, Codex's concrete build action and result, then the user's verification or revision request. Do not show a dialogue box or a raw transcript. Codex may connect another named tool or service, but the Step must still show the reader directing the build through Codex.
9. Write each Step title as a concise Korean noun phrase that names the meaningful work unit. The final word must belong to this exact noun allowlist: `준비`, `분석`, `설계`, `구성`, `구현`, `연결`, `설정`, `생성`, `검증`, `수정`, `테스트`, `설치`, `배포`, `실행`, `적용`, or `활용`. Use `실제 양식과 업무 자료 준비` and `생성 결과 검증과 오류 수정`, not `자료를 준비합니다` or `자료 준비하기`.
10. Keep Step prose as practical present-tense honorifics. Show what the reader prepares, asks Codex to make, and checks in the result. Do not write retrospective development reports such as `Codex가 구현했습니다` or `시스템을 완성했습니다`.

## Synthesize a Manuscript Version

This section applies only to `book_a4`.

Triggers include `Part 1-01 원고로 합성해줘`, `이 프로젝트 재료로 원고를 만들어줘`, and `실제 결과물을 만들고 이미지 포함 원고로 완성해줘`.

1. Read only the material cards named by the user. If none are named, use active cards in the registered project's `00 Conversations` bundles.
2. Reconcile duplicates, uncertainty, and conflicts. Keep unsupported claims out of publication prose.
3. Run the New Book A4 Routing Contract and allocate the next version with `scripts/next_version.py`. Create a fresh `v0.N` only.
4. Write `production-plan.json` with in-scope deliverables, acceptance checks, and the dynamic build Steps.
5. Create, run, test, and correct the planned deliverables before marking their artifacts `verified`.
6. Write `<title>.md`, `manuscript.json`, and `asset-manifest.json` using `references/manuscript-schema.md` and `references/asset-policy.md`.
7. For a new A4 package, write `template_version: 3`, `editorial_quality_version: 3`, flexible `practice_blocks`, and `editorial_review` before requesting images. Read `references/master-editorial-profile.md` and confirm the V3 preflight passes before calling image generation.
8. Preserve this fixed editorial order:

```text
챕터 제목
[이번 챕터에서는]
[한눈에 보기]
[미리 보기]
[실습하기]
Step 1 ... Step N
[실전 활용하기]
[꿀팁 더하기]
필요한 마지막 주의 문구
```

9. Keep the four-row quick-reference table, preview/QR panel, Step image positions, inter-step tip boxes, and final caution area. Add a real-world-use image only when it is supported by the material and useful to the section. Do not add unrelated editorial sections.

## Required AI Image Workflow

This section applies only to `book_a4`. Historical V1 packages require one preview image, one image per Step, and one real-world-use image: `len(steps) + 2`. Newly synthesized V2 packages require one preview image, one preparation image, and one image per Step; a real-world-use image is added only when the source material supports a useful field application visual.

## Book A4 Template Version 2

Every newly synthesized A4 manuscript uses `template_version: 3`. This branch preserves historical V1/V2 `book_a4` packages and does not alter the adaptive blog profile.

V2 keeps the chapter title, `[이번 챕터에서는]`, `[한눈에 보기]`, `[미리 보기]`, `[실습하기]`, `[실전 활용하기]`, and optional caution areas. Inside `[실습하기]`, store an ordered `practice_blocks` list in the form `step, tip, step, tip, ... step`. Step count remains dynamic, and N Steps require exactly N-1 tips; no tip follows the final Step.

Each V2 Step body contains exactly two or three sentences. The content must show the reader preparing or requesting work, the relevant AI agent creating or changing the technology, and the reader checking the observable completion condition. A Step that only uses an already completed service belongs in `[실전 활용하기]`.

V2 historical packages retain their original preview/preparation/Step visual contract. V3 requires topic-specific wide Codex-generated explanatory images with a visual brief, clean composition, immediate captions, and no automatically added numbers, arrows, red boxes, borders, or other instructional overlays.

1. Finalize the manuscript Step meanings before generating images.
2. For every slot, use the `imagegen` skill and Codex built-in image generation. Do not use an external image API or request a user API key.
3. Before prompting, choose one visual kind for each slot: `ui_screen` for a setting or execution screen, `work_product` for files or code, `workflow_diagram` for an automation flow, `result_preview` for a finished output, or `field_scene` for school use. Make the prompt specific to the current artifact and build change. Generic laptop, teacher, or classroom decoration is insufficient.
4. Every prompt must request `wide landscape composition, 16:9`, a professional editorial layout, and a realistic software or document presentation appropriate to its visual kind. Explicitly prohibit robots, holograms, glowing brains, neon interfaces, floating icons, invented menus, unreadable Korean, and unrelated charts. UI images use only short verified labels, never long generated Korean paragraphs. The saved image must be at least 1200px wide with a pixel width-to-height ratio of at least `1.5`.
5. Inspect each generated source at original size with `view_image` before selecting it. Confirm purpose match, professional layout, legible content, absence of generation artifacts, and absence of generic AI motifs. Record those five checks and a concise review note in both the visual metadata and asset manifest. Revise a failed prompt once; a second failure stops publication.
6. Save each selected PNG or JPEG under the version-local `assets/` folder. Give every slot a unique `asset_id`.
7. Record `method: generated_scene`, visual kind, generation prompt, version-local output path, lowercase SHA-256, evidence kind, privacy status, and the completed quality review in `asset-manifest.json`.
8. Give every image a numbered editorial caption in render order: `그림 Part-챕터-순번. 설명`. Place it immediately below its image. State the visible artifact, workflow state, result, or completion check. Do not call a generated visual an actual screenshot, and do not force all captions to say `예시 이미지` or `재현 화면`.
9. Do not create a blank panel, image placeholder, or partially illustrated manuscript.

## Validate, Render, and Publish

This section applies only to `book_a4`.

1. Run `scripts/validate_manuscript.py manuscript.json asset-manifest.json asset-validation.json`.
2. Accept only `status: ready`. Require `asset-validation.json.validated_inputs` to contain the current SHA-256 values of both `manuscript.json` and `asset-manifest.json`; any later change makes the report stale and requires validation again. The validator requires the Flexible Build-Step Contract, nominal Step titles, practical present-tense Step prose, the three-part Codex interaction, and every generated image slot. It checks unique IDs, visual kinds, quality reviews, professional prompts, numbered immediate captions, width, landscape ratio, version-local paths, PNG/JPEG signatures, and SHA-256 values.
3. Run `scripts/render_manuscript.py manuscript.json <version-folder>` only after validation is ready. It produces A4 portrait `manuscript.html` and `manuscript.pdf` with no image fallback.
4. Keep the local version folder as the source of truth. Set `manuscript.json.output_profile` to `book_a4` and `source_markdown` to the exact version-root Markdown filename. Before any REST request, `scripts/publish_manuscript_version.py` enforces the exact publication allowlist: `production-plan.json`, that one source Markdown file, `manuscript.json`, `asset-manifest.json`, `asset-validation.json`, `manuscript.html`, `manuscript.pdf`, and manifest-listed assets only. Missing or additional files stop publication. It must snapshot every allowed file before the first REST request and upload only those immutable byte snapshots.
5. Publish text through the text route and images/PDF through the opaque binary route. Require byte-for-byte readback and SHA-256 equality for every file.
6. If any upload fails, preserve every remote file that may already have been written and record the verified and incomplete paths in `publication-validation.json`. Never delete or roll back remote files automatically because the Local REST API does not provide conditional write ownership. Report `publication_failed`, leave the failed local version unchanged for diagnosis, and retry only by allocating a fresh immutable version; never substitute a workspace file or another version.

## Synthesize an Adaptive Blog Version

Triggers include `이 대화 재료로 플랫폼 독립 범용 블로그형을 만들어줘`, `블로그 버전으로 만들어줘`, and `Markdown과 HTML 블로그로 만들어줘`.

1. Confirm that `adaptive_blog` was explicitly selected. Read only the material cards named by the user; when none are named, use active cards in the registered project's `00 Conversations` bundles.
2. Read `references/blog-schema.md` and `references/blog-editorial-policy.md`. Do not load the A4 Step structure, fixed book sections, book image formula, or PDF renderer into this branch.
3. Reconcile duplicate claims and conflicting evidence. Choose exactly one source-supported mode: `practical_guide`, `case_story`, or `insight_column`. Record the reason in `mode_reason` without exposing it in the public article.
4. Normalize a safe lowercase ASCII `topic-slug`, resolve the blog root as `02 Blog/<topic-slug>`, and use `scripts/next_version.py` to allocate a fresh `02 Blog/<topic-slug>/v0.N`. Never reuse or overwrite an earlier blog version.
5. Write `blog.json` and `asset-manifest.json`. Use five to seven ordered sections. Give every section exactly one role from the selected mode, include all five required roles in canonical order, and repeat a role only in an adjacent section when the topic needs six or seven sections. Do not use a `roles` array, a `supporting` role, or an unknown role.
6. Give every evidence point a unique `evidence_id`. Before writing `blog.json`, compare every `source_refs` value with the active conversation bundle's stable turn IDs and attachment or file entries. Reject unresolved source_refs instead of inventing or repairing them. Make `lead_evidence_refs` and every section's `evidence_refs` resolve to those IDs; when first-person experience is source-supported, make `first_person_evidence_refs` resolve only to verified `observation` evidence. Preserve verified files, commands, errors, decisions, results, and limitations. Do not fabricate first-person experience or imitate a named writer's distinctive voice.
7. Store article body content as plain paragraph blocks only. Do not place raw Markdown lists, fenced code, or raw HTML in `paragraphs`; the renderer escapes content syntax instead of interpreting it.
8. Add exactly one hero visual and zero to four evidence-bearing section visuals. Use a cleared `provided_asset` with provenance when suitable source material exists, or use the `imagegen` skill for a professional `generated_scene`. Every generated image must use the required landscape editorial prompt, carry the exact internal disclosure `AI 생성 설명 이미지` in both visual metadata and the manifest, pass original-size visual inspection, and never be described as an actual screenshot in public alt text or captions.
9. Run `scripts/validate_blog.py blog.json asset-manifest.json blog-validation.json`. Continue only when it returns `status: ready`; otherwise keep the last verified version unchanged and report the deterministic error codes.
10. Run `scripts/render_blog.py blog.json <version-folder>`. It produces portable `blog.md` and semantic `blog.html` only. Do not create a PDF for this profile.
11. Keep the local version folder as the source of truth. Run `scripts/publish_manuscript_version.py` with the Vault destination `02 Blog/<topic-slug>/v0.N`; the generic publisher must snapshot its exact allowlist before the first REST request, upload every text and binary snapshot through Local REST, and create `publication-validation.json` only after byte-for-byte readback succeeds. A partial failure is preserved and retried only in a fresh immutable version, never by deleting uncertain remote content or overwriting the failed version.
12. Report the selected mode, exact version path, evidence count, image count, `blog-validation.json` status, and `publication-validation.json` status. Never claim that the article defeats an AI detector or is guaranteed to be indistinguishable from a person.

## Deterministic Error Codes

Report the exact machine-readable code when a validation, rendering, publication, or export step stops. The current documented contract includes `blog_profile_required`, `insufficient_evidence`, `asset_hash_mismatch`, `image_generation_failed`, `validation_not_ready`, `stale_validation`, `unexpected_source_file`, `unsafe_path`, and `immutable_export_conflict`. The profile references list the complete validator-specific code tables; do not invent a new code in a user-facing report.

`image_generation_failed` means the image prompt was revised once and the second generation still failed. Stop Markdown finalization, HTML/PDF rendering, and Vault publication; never substitute a blank panel or partial manuscript.

## Verified Desktop Publication Library

Read `references/publication-library.md` whenever a verified book or blog must be placed in the copy-ready desktop publication library. This export is separate from the Obsidian Vault and never changes the immutable source version.

For both profiles, enforce this exact order: `validation → render → Vault publication attempt → desktop export`.

1. Do not invoke the desktop exporter until the selected profile's validation report has `status: ready`, its `validated_inputs` still match the current metadata and asset manifest, and its renderer has produced every required file. A book requires its source Markdown, `manuscript.html`, and `manuscript.pdf`; a blog requires `blog.md` and `blog.html` and must not have a desktop PDF.
2. Read `vaultPath` and `publicationRoot` from the runtime configuration. Read `destination_root` from the exact registered project. Never infer the project directory from a title and never pass a Local REST API key, certificate, or plugin configuration contents to the exporter.
3. Attempt Vault publication when Local REST is available and record `vault_publication_status`. A Vault REST failure does not block desktop export when the selected local package remains freshly validated and fully rendered.
4. Run exactly one selected version through:

```text
scripts/export_publication_bundle.py
  --source-version-dir <absolute selected v0.N folder>
  --publication-root <absolute runtime publicationRoot>
  --project-destination-root <exact registry destination_root>
  --vault-path <absolute runtime vaultPath>
```

5. Record `desktop_export_status` from the exporter as `exported`, `history_exported`, `already_exported`, or `export_failed`. Validation, render, or export failure never claims completion and never changes the prior verified desktop `00 최신본`.
6. Report `vault_publication_status` and `desktop_export_status` as separate lines, followed by the output profile, immutable source version, and final desktop path. Never describe successful desktop export as successful Vault publication.

For the complete maintenance pipeline, use `scripts/finalize_publication.py` so fresh validation, native rendering, the Local REST publication attempt, and Desktop export remain in that order. For repository-to-installed-runtime maintenance, use `scripts/verify_skill_sync.py` only after the release tests pass; compare non-generated files by SHA-256 and preserve the previous installed copy as a backup.

Use these explicit routes:

- `바탕화면 출판함만 다시 만들어줘`: re-export only the exact already-verified version established by the active request. Do not regenerate content or images.
- `v0.N 검증본을 출판함에 정리해줘`: backfill only the named immutable version.

For either route, require the exact project, profile, and version. Never scan all historical versions implicitly. If the request is ambiguous, obtain the missing selector before exporting anything.

## Delete Current Conversation Bundle

Triggers include `이 대화의 옵시디언 자료를 전부 삭제해줘` and `이 대화 옵시디언 폴더를 지워줘`.

1. Treat the explicit delete request as approval for the active conversation bundle only.
2. Read the active task/thread ID and use it as the exact `conversation_key`. Never identify a delete target from title, topic, or a similar card.
3. Resolve the registered project's `00 Conversations` root and run:

```text
scripts/delete_conversation_bundle.py
  --config <Local REST API data.json>
  --conversations-root <vault-relative project/00 Conversations>
  --conversation-key <active exact thread ID>
  --vault-root <absolute Obsidian Vault path>
```

4. The script validates the key, recursively lists only that exact bundle, checks `metadata.json`, deletes files through REST deepest-first, requires 404 readback for every deleted file, and verifies an unrelated sibling conversation remains byte-identical.
5. Because the Local REST API deletes files but leaves empty directories on Windows, remove only the verified-empty exact bundle directories after REST deletion. Refuse this cleanup if any file or symbolic link remains or if the normalized target is not the exact child of the configured conversations root.
6. Report `deleted` only when the complete bundle is absent. Report `already_absent` when it was already gone. Report `partial_delete_failed` with remaining paths when any file survives.
7. Never delete an independent versioned manuscript. A later save request recreates the deleted conversation bundle from the full active task.
8. Never delete Vault files directly from the filesystem; the only filesystem cleanup allowed is `rmdir` on the verified-empty exact bundle after REST file deletion succeeds.

## Editorial Voice

1. Write the final Korean manuscript in natural 존댓말. Vary `합니다`, `할 수 있습니다`, `해야 합니다`, `해 봅니다`, and `확인합니다` without repetitive padding.
2. `[이번 챕터에서는]`, every Step, `[실전 활용하기]`, and `[꿀팁 더하기]` are each one paragraph of two or three sentences.
3. Frame the title and `[이번 챕터에서는]` around the concrete technology being made: Skill, plugin, MCP server, AI Agent, automation, web app, data pipeline, or document generator. Do not frame a build chapter as a finished-tool usage guide.
4. Name the actual primary tool from the materials. Do not force Codex into a chapter using another tool; distinguish the user, AI agent, code, and external service.
5. Describe delegation accurately: the user supplies goals, materials, rules, exceptions, and final judgment; the tool or agent analyzes, plans, creates, runs, tests, and corrects within authorization.
6. Do not claim one-request perfection, human-free operation, guaranteed accuracy, or autonomous correction. The user verifies real work rules, privacy, security, cost, permissions, and final suitability.
7. Preserve verified names, functions, commands, sequences, and results. Use `확인 필요` outside final publication prose when a fact is unsupported.
8. Use image captions for completion checks, cautions, or distinctions, not to repeat the paragraph.
9. Make generated visuals look like professional educational-technology publishing assets. Select an actual screen, work product, workflow, result preview, or field scene based on the current purpose; never use generic AI decoration as a substitute for evidence.

## Exclude or Pause

- `이번 작업은 저장하지 마`: do not archive, refresh, synthesize, or publish the active task.
- `이 프로젝트 원고화 중지해줘`: change only the named registry entry to `paused`.

## Safety

## Master Editorial Quality V3 Override

For new synthesis, this section overrides historical V2-only wording above. Read `references/master-editorial-profile.md` before creating a Book or Blog V3 package. New books use `template_version: 3` and `editorial_quality_version: 3`; new blogs use `editorial_quality_version: 3`. V3 Step count and tip placement follow the real build evidence, Step bodies contain 2-4 sentences, and sufficiently detailed tips contain 3-5 sentences. Every new V3 visual is a topic-specific Codex-generated `generated_scene` with a `visual_brief`; it must be wide, plausible, print-legible, and free of `red_box`, `numbered_callout`, `arrow`, borders, generic AI motifs, and invented unreadable interface text. A score below 85 or any hard failure stops rendering and publication. V1/V2 and historical blog contracts remain available only when explicitly selected or when opening an existing immutable version.

- Never expose student names, contact details, API keys, tokens, private school records, or unrelated desktop content.
- Never scan all Codex conversations.
- Never overwrite a finished version.
- Never call unverified output complete.
- Never delete during archive, refresh, synthesis, render, or publish. Deletion occurs only through the explicit Delete Current Conversation Bundle trigger.
