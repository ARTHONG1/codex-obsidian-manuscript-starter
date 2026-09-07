# Book A4 V2 Interleaved Tips and Realistic Visuals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Add a backward-compatible A4 manuscript V2 for two/three-sentence build Steps, inter-step tips, and wide professional AI-generated visuals.

**Architecture:** Keep legacy `book_a4` behavior intact and route only `template_version: 2` packages through V2 validation and rendering. Represent practice content as ordered Step/Tip blocks so dynamic Step counts and exact inter-step placement are machine-checkable.

**Tech Stack:** Python 3, unittest, Pillow, ReportLab, existing Codex image generation, existing JSON manifests, HTML/CSS, PowerShell repository contracts.

## Global Constraints

- Do not change conversation storage, deletion, Local REST, binary readback, immutable versions, blog output, installation, or desktop publication behavior.
- Do not overwrite historical V1 packages.
- Use Codex built-in image generation only; do not add an external image API.
- V2 requires preview, preparation, and one wide visual per Step; real-world-use visual is optional.
- Every Step body has exactly 2 or 3 sentences.
- N Steps require exactly N-1 inter-step tips.
- Generated images must be wide, at least 1200px, and pass manifest/hash/quality checks.
- No completion claim without fresh test and rendered-output evidence.

---

### Task 1: Freeze legacy behavior with characterization tests

**Files:**
- Test: `tests/test_manuscript_renderer.py`
- Test: `tests/test_publish_manuscript_version.py`
- Test: `tests/test_desktop_publication_export.py`
- Test: `tests/test_obsidian_manuscript_workspace.py`
- Read-only audit: all conversation, deletion, REST, and blog tests

**Interfaces:**
- Consumes existing V1 fixtures and current `book_a4` JSON.
- Produces named regression tests proving old renderer, publisher, exporter, blog, and storage contracts remain unchanged.

- [ ] Write assertions that a V1 package still validates and renders through the existing path.
- [ ] Write assertions that the V1 package still requires its historical fields.
- [ ] Write assertions that blog, deletion, REST, and export tests are not routed through V2.
- [ ] Run the focused tests and record the baseline counts.
- [ ] Define the diff allowlist for later implementation review.

**Review gate:** No V2 implementation begins until the legacy baseline is recorded.

### Task 2: Add the V2 schema and version selector

**Files:**
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/manuscript-schema.md`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/validate_manuscript.py`
- Test: `tests/test_manuscript_renderer.py`

**Interfaces:**
- Input: `output_profile: book_a4`, `template_version: 2`, and `practice_blocks`.
- Output: deterministic V2 validation errors and a ready report containing current manuscript and manifest hashes.

- [ ] Add a failing fixture for a valid V2 Step/Tip sequence.
- [ ] Add failing assertions for missing version, malformed blocks, skipped Step numbers, duplicate tips, and tip after the final Step.
- [ ] Implement version dispatch without changing V1 field validation.
- [ ] Require Step artifacts, completion checks, interaction fields, and visual metadata in V2.
- [ ] Run V2 validator tests and then the legacy validator tests.

**Review gate:** V1 and V2 fixtures must be distinguishable by explicit version data; no heuristic topic detection is allowed.

### Task 3: Enforce editorial Step and tip contracts

**Files:**
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/validate_manuscript.py`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/manuscript-schema.md`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/SKILL.md`
- Test: `tests/test_manuscript_renderer.py`
- Test: `tests/test_documentation_contract.py`

**Interfaces:**
- Input: Step `body` as a two- or three-element sentence list or the explicitly supported normalized representation.
- Output: validation codes for sentence count, block order, missing tip, tip duplication, and non-specific tip content.

- [ ] Add RED tests for one sentence, four sentences, punctuation in paths/versions, and an N-step/N-2-tip sequence.
- [ ] Define sentence counting at the normalized content boundary and document exclusions for URLs, file paths, decimals, and abbreviations.
- [ ] Implement exact N-1 tip validation between Steps.
- [ ] Implement duplicate/generic tip detection only to the extent reliably supported by existing text rules.
- [ ] Add tests for the user-request → agent-action → user-check ordering.
- [ ] Run focused editorial tests and documentation contracts.

**Review gate:** The validator must not reject valid Korean prose merely because a path, version number, or URL contains periods.

### Task 4: Extend the asset contract for realistic V2 visuals

**Files:**
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/asset-policy.md`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/validate_manuscript.py`
- Test: `tests/test_manuscript_renderer.py`

**Interfaces:**
- Input: V2 visual metadata, version-local image files, manifest records, and optional deterministic overlay metadata.
- Output: validated visual slots with method, prompt, kind, dimensions, hash, disclosure, and quality review.

- [ ] Add RED tests for missing preparation visual, portrait image, low width, unreadable image, missing caption, missing prompt, and path escape.
- [ ] Define the V2 slot enumeration: preview, preparation, Step 1..N, optional real-world use.
- [ ] Add fields for base-generation prompt and deterministic overlay description without exposing secrets.
- [ ] Preserve `generated_scene` provenance and truthful disclosure.
- [ ] Keep binary signature and SHA-256 checks unchanged for existing packages.
- [ ] Run focused asset tests and old asset fixtures.

**Review gate:** AI-generated visuals are never described as actual screenshots, and no visual failure is silently replaced.

### Task 5: Render V2 HTML blocks

**Files:**
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/render_manuscript.py`
- Test: `tests/test_manuscript_renderer.py`

**Interfaces:**
- Input: ready V2 manuscript JSON and asset manifest.
- Output: A4 portrait HTML with ordered Step, image, caption, tip, and next-Step blocks.

- [ ] Add a RED test asserting the expected HTML order for Step 1 → Tip 1 → Step 2.
- [ ] Add a RED test asserting every image is immediately followed by its caption.
- [ ] Implement a V2 render branch selected only by `template_version: 2`.
- [ ] Render wide images with constrained dimensions and preserve caption placement.
- [ ] Add CSS grouping rules to keep Step headings, body, visual, and caption together where possible.
- [ ] Run HTML structure and legacy HTML tests.

**Review gate:** V1 HTML output remains byte-compatible where existing tests require it; V2 must not render the legacy final tip in addition to inter-step tips.

### Task 6: Render V2 PDF layout

**Files:**
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/render_manuscript.py`
- Test: `tests/test_manuscript_renderer.py`
- Test fixture: existing temporary manuscript fixture factory, extended only if necessary

**Interfaces:**
- Input: validated V2 JSON and version-local assets.
- Output: deterministic A4 portrait PDF with the same semantic order as HTML.

- [ ] Add a RED test that extracts PDF text and checks Step/Tip order.
- [ ] Add a RED test for long Step content and page-break grouping.
- [ ] Implement V2 ReportLab flowables for Step, visual, caption, and tip.
- [ ] Preserve the existing footer, typography, green labels, and preview panel where the legacy contract requires them.
- [ ] Render a short, medium, and large Step-count fixture.
- [ ] Render PDF pages to PNG and inspect every page at original size.

**Review gate:** No heading, image, or caption may be orphaned by the V2 page-break strategy.

### Task 7: Connect V2 to publication and desktop export without broadening allowlists

**Files:**
- Modify only if required: `scripts/publish_manuscript_version.py`
- Modify only if required: `scripts/export_publication_bundle.py`
- Test: `tests/test_publish_manuscript_version.py`
- Test: `tests/test_desktop_publication_export.py`

**Interfaces:**
- Input: a ready V2 local version folder.
- Output: the same exact allowlisted publication package and copy-ready desktop bundle, with V2 practice order preserved.

- [ ] Add a failing test for V2 package acceptance with exact allowed files.
- [ ] Add a failing test for an unlisted asset and stale validation hash.
- [ ] Implement the smallest profile/version-aware change possible.
- [ ] Verify binary assets and PDF continue through the existing binary route.
- [ ] Verify failed publication preserves local and remote partial-state rules.
- [ ] Run publisher and exporter tests for both V1 and V2.

**Review gate:** No change is allowed to conversation storage, REST, deletion, or immutable-version semantics.

### Task 8: Update editorial skill documentation and contracts

**Files:**
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/SKILL.md`
- Modify: `references/manuscript-schema.md`
- Modify: `references/asset-policy.md`
- Test: `tests/test_documentation_contract.py`
- Test: `tests/test_obsidian_manuscript_workspace.py`

**Interfaces:**
- Input: verified V2 implementation behavior.
- Output: discoverable, unambiguous instructions for future Codex runs.

- [ ] Add documentation tests for the V2 trigger, block sequence, sentence rule, visual rule, and compatibility boundary.
- [ ] Replace only the `book_a4` synthesis instructions that need version-specific routing.
- [ ] Keep blog instructions and non-manuscript workflows unchanged.
- [ ] Document that generated visuals are explanatory and not actual captures.
- [ ] Run documentation and workspace contracts.

**Review gate:** Documentation must describe tested behavior, not intended behavior.

### Task 9: Full regression and visual verification

**Files:**
- Test additions only in the existing relevant test files.
- Verification output in the planning/progress records, not product code.

**Interfaces:**
- Input: repository with V2 changes in an isolated implementation worktree.
- Output: fresh evidence for unit tests, syntax, documentation, rendered pages, hashes, and forbidden-diff audit.

- [ ] Run the complete Python suite.
- [ ] Run installer and secret-scan contracts.
- [ ] Compile every changed Python file in memory.
- [ ] Run `git diff --check`.
- [ ] Render V1 and V2 PDFs to page images and inspect them.
- [ ] Check that no API key, certificate, Vault path, or personal attachment entered generated files.
- [ ] Check the diff against the frozen subsystem allowlist.
- [ ] Record failures and rerun only after root-cause changes.

**Review gate:** Completion requires command output and visual evidence; agent reports alone are insufficient.

### Task 10: Synchronize and release only after approval

**Files:**
- Repository skill mirror and installed skill are implementation-release targets only.
- No release file is modified during this planning task.

**Interfaces:**
- Input: verified repository implementation and explicit release approval.
- Output: hash-equal repository/installed skill trees and a release-ready checklist.

- [ ] Compare every deployable repository and installed skill file by SHA-256.
- [ ] Verify no `__pycache__`, runtime config, Vault content, credentials, or private images are included.
- [ ] Confirm version metadata and changelog scope.
- [ ] Prepare, but do not execute, the commit/tag/push commands unless separately authorized.

**Review gate:** This task is outside the current planning-only execution and must not run now.

## Required final verification matrix

| Area | Required evidence |
|---|---|
| V1 compatibility | Existing V1 fixture validates and renders |
| V2 schema | Valid sequence passes; malformed sequence fails deterministically |
| Editorial | Every Step has 2–3 sentences; N Steps have N−1 inter-step tips |
| Visuals | Preview, preparation, and every Step image are wide, readable, hashed, and manifest-listed |
| HTML | Step → image → caption → tip order is present |
| PDF | Same semantic order survives pagination and page rendering |
| Publication | Exact allowlist, stale hashes, binary readback, and partial-failure rules pass |
| Regression | Blog, storage, deletion, REST, installation, and desktop export tests remain green |
| Security | No credentials, private paths, or unrelated user data enter the package |

## Open decisions for implementation review

1. Whether the version marker should be `template_version: 2` or a distinct `output_profile: book_a4_v2`; recommendation is `template_version: 2` to preserve existing publisher routing.
2. Whether V2 keeps the legacy four-row quick-reference and QR panel exactly; recommendation is yes.
3. Whether `[실전 활용하기]` needs an image for a specific chapter; recommendation is optional and evidence-driven.
4. Whether generated visual post-processing uses Pillow or an existing image utility; recommendation is to reuse existing dependencies and avoid a new package.
