---
name: obsidian-manuscript-publisher
description: Use when a user wants to register an Obsidian manuscript project, save or refresh the current Codex conversation, synthesize and publish an A4 manuscript, remove the current conversation's Obsidian bundle, exclude one task, or pause a manuscript project.
---

# Obsidian Manuscript Publisher

Use Obsidian as both an auditable conversation source and an editorial manuscript workspace. Keep every Codex conversation isolated by its exact task/thread ID, convert only verified technology-building work into manuscript Steps, and never report success before deterministic validation passes.

## Runtime Configuration

- Read the user-local runtime configuration from `%LOCALAPPDATA%\CodexObsidianManuscript\runtime.json`. It stores only the selected Vault path and the Local REST plugin configuration path; it never stores or prints an API key.
- Resolve the Vault, registry, unit template, and Local REST configuration from that file. The registry is `<Vault>\_system\manuscript-projects.json`, the unit template is `<Vault>\02 Templates\원고 단위 템플릿.md`, and the conversation root inside each registered project is `00 Conversations/<conversation_key>`.
- If the runtime configuration is missing, malformed, or points outside the configured Vault, do not guess paths and do not write directly to disk. Tell the user to run `bootstrap\install-windows.ps1` from the published starter repository, then `bootstrap\doctor.ps1` with Obsidian open.

## Non-Negotiable Contracts

1. Work only with the active Codex task and an explicitly registered manuscript project. Never infer a project from title or topic keywords and never scan unrelated tasks.
2. Use the active task/thread ID as `conversation_key`. Different IDs always produce different folders, even when titles and topics match.
3. Save Vault content only through the installed local Obsidian REST API on `127.0.0.1`. Do not use direct filesystem writes, `Copy-Item`, or delayed workspace fallbacks for Vault publication.
4. Require byte-for-byte readback for text and binary uploads. Require SHA-256 equality when publishing a manuscript version.
5. Keep manuscript versions immutable. Allocate a new `v0.N`; never overwrite an earlier draft.
6. Keep Step count dynamic. Use Step 1 through Step N according to the actual verified build workflow.
7. New manuscript visuals use `generated_scene only`, created with Codex built-in image generation. The required image count is `len(steps) + 2`.
8. Do not render HTML/PDF or publish a version while any required image is absent, invalid, duplicated, unrelated to its Step, or unverified.

## Register a Project

Trigger: `이 프로젝트를 원고 프로젝트로 등록해줘` or equivalent.

1. Identify the exact Codex project, book, Part, chapter, template, and Vault-relative project folder.
2. Add or update only that project entry in the registry.
3. Create the project brief, `00 Conversations`, and `01 Manuscript` locations through the local REST API when absent.
4. Report the registered source project and destination. Do not change other registry entries.

## Archive and Refresh the Current Conversation

Triggers include `이 대화 전체를 옵시디언에 저장해줘`, `이 대화 원고 재료 최신화해줘`, and `이 대화 옵시디언에 정리해줘`.

1. Confirm the active task belongs to a registered project.
2. Use `codex_app__read_thread` or the active Codex thread-reading capability, include readable outputs, and follow cursors until no older turn remains. Never scan other Codex threads.
3. Normalize user, assistant, and readable tool-output turns with stable turn IDs.
4. Run `scripts/archive_conversation.py` against a staging `00 Conversations` root. The script creates exactly:

```text
00 Conversations/<conversation_key>/
├─ conversation.md
├─ material-card.md
├─ metadata.json
└─ assets/
```

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
4. Name the chapter after the technology the reader will make with Codex, such as `Codex로 교육 뉴스 수집 Skill 만들기`, rather than after using an already completed service.
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

## Synthesize a Manuscript Version

Triggers include `Part 1-01 원고로 합성해줘`, `이 프로젝트 재료로 원고를 만들어줘`, and `실제 결과물을 만들고 이미지 포함 원고로 완성해줘`.

1. Read only the material cards named by the user. If none are named, use active cards in the registered project's `00 Conversations` bundles.
2. Reconcile duplicates, uncertainty, and conflicts. Keep unsupported claims out of publication prose.
3. Allocate the next version with `scripts/next_version.py`. Create a fresh `v0.N` only.
4. Write `production-plan.json` with in-scope deliverables, acceptance checks, and the dynamic build Steps.
5. Create, run, test, and correct the planned deliverables before marking their artifacts `verified`.
6. Write `<title>.md`, `manuscript.json`, and `asset-manifest.json` using `references/manuscript-schema.md` and `references/asset-policy.md`.
7. Preserve this fixed editorial order:

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

8. Keep the four-row quick-reference table, preview/QR panel, Step image positions, real-world-use image, tip box, and final caution area. Do not add unrelated editorial sections.

## Required AI Image Workflow

Every manuscript version requires one preview image, one image per Step, and one real-world-use image. The total is `len(steps) + 2`.

1. Finalize the manuscript Step meanings before generating images.
2. For every slot, use the `imagegen` skill and Codex built-in image generation. Do not use an external image API or request a user API key.
3. Make each prompt specific to the current artifact and build change. Show the Skill structure, plugin modules, agent flow, configuration relationship, test state, correction, or school-use scene that belongs to that slot. Generic laptop, teacher, or classroom decoration is insufficient. Every prompt must request `wide landscape composition, 16:9`; the saved image must have a pixel width-to-height ratio of at least `1.5`.
4. Save each selected PNG or JPEG under the version-local `assets/` folder. Give every slot a unique `asset_id`.
5. Record `method: generated_scene`, generation prompt, version-local output path, lowercase SHA-256, evidence kind, and privacy status in `asset-manifest.json`.
6. Give every generated illustration one caption beginning with `예시 이미지` or `예시 화면`, placed immediately below that image. State the artifact or completion check visible in the image; never present it as a verified real interface or guaranteed result.
7. If generation fails, change the prompt based on the failure and retry once. If it fails again, report `image_generation_failed` and stop before Markdown finalization, HTML/PDF rendering, or Vault publication.
8. Do not create a blank panel, image placeholder, or partially illustrated manuscript.

## Validate, Render, and Publish

1. Run `scripts/validate_manuscript.py manuscript.json asset-manifest.json asset-validation.json`.
2. Accept only `status: ready`. The validator requires the Flexible Build-Step Contract, the three-part Codex interaction, and every generated image slot. It checks unique IDs, prompts, immediate captions, landscape ratio, version-local paths, PNG/JPEG signatures, and SHA-256 values.
3. Run `scripts/render_manuscript.py manuscript.json <version-folder>` only after validation is ready. It produces A4 portrait `manuscript.html` and `manuscript.pdf` with no image fallback.
4. Keep the local version folder as the source of truth. Run `scripts/publish_manuscript_version.py` to publish Markdown, JSON, HTML, PDF, manifests, and assets.
5. Publish text through the text route and images/PDF through the opaque binary route. Require byte-for-byte readback and SHA-256 equality for every file.
6. Report `published` only after `publication-validation.json` confirms all files. Otherwise report `publication_failed`; never substitute a workspace file or another version.

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

## Exclude or Pause

- `이번 작업은 저장하지 마`: do not archive, refresh, synthesize, or publish the active task.
- `이 프로젝트 원고화 중지해줘`: change only the named registry entry to `paused`.

## Safety

- Never expose student names, contact details, API keys, tokens, private school records, or unrelated desktop content.
- Never scan all Codex conversations.
- Never overwrite a finished version.
- Never call unverified output complete.
- Never delete during archive, refresh, synthesis, render, or publish. Deletion occurs only through the explicit Delete Current Conversation Bundle trigger.
