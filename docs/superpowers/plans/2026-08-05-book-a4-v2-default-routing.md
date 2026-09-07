# Book A4 V2 Default Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every newly synthesized A4 manuscript use `template_version: 2` by default while preserving historical V1 manuscripts for validation, rendering, and publication.

**Architecture:** Keep `output_profile: book_a4` as the public profile and use `template_version` only for template routing. The synthesis skill selects V2 unconditionally for new manuscripts unless the user explicitly requests the legacy template; validator and renderer retain their V1 compatibility branches for immutable historical versions.

**Tech Stack:** Codex skill Markdown, Python 3, unittest, JSON manuscript contracts, existing V1/V2 validators and renderers.

## Global Constraints

- Never overwrite or rewrite an existing immutable V1 or V2 manuscript version.
- Preserve conversation storage, material cards, Local REST, binary readback, deletion, adaptive blog, installation, and desktop publication behavior.
- New A4 synthesis means a newly allocated `v0.N`, not a historical version being revalidated or re-exported.
- Every newly synthesized A4 manuscript must contain `output_profile: book_a4` and `template_version: 2`.
- V1 is selected only by an explicit request containing `기존 양식`, `레거시 양식`, `V1`, or an equivalent unambiguous legacy selector.
- A generic request such as `원고를 만들어줘`, `A4 원고로 합성해줘`, or `다음 버전을 만들어줘` selects V2.
- The existing published `v0.2` remains unchanged; a corrected manuscript is allocated as a fresh `v0.3` or the next available immutable version.

---

### Task 1: Capture the routing defect with failing contract tests

**Files:**
- Modify: `tests/test_obsidian_manuscript_workspace.py`
- Modify: `tests/test_documentation_contract.py`
- Read: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/SKILL.md`
- Read: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/manuscript-schema.md`

**Interfaces:**
- Consumes: repository skill and schema text.
- Produces: tests that fail while generic A4 synthesis can still resolve to V1.

- [ ] Add `test_new_a4_synthesis_defaults_to_template_version_2` asserting the skill contains an exact normative rule equivalent to `Every newly synthesized book_a4 manuscript MUST set template_version: 2`.
- [ ] Add `test_legacy_v1_requires_an_explicit_user_selector` asserting that V1 is described only as historical compatibility or an explicit legacy request.
- [ ] Add `test_generic_manuscript_prompts_route_to_v2` covering the three generic Korean prompt examples.
- [ ] Add `test_legacy_fixed_order_is_scoped_to_v1` so the old final-tip and required real-world-image rules cannot appear as unqualified book defaults.
- [ ] Run `python -m unittest tests.test_obsidian_manuscript_workspace tests.test_documentation_contract -v`.
- [ ] Confirm RED failures identify the current ambiguous default, not spelling or fixture errors.

### Task 2: Make V2 the single default synthesis contract

**Files:**
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/SKILL.md`
- Test: `tests/test_obsidian_manuscript_workspace.py`
- Test: `tests/test_documentation_contract.py`

**Interfaces:**
- Consumes: generic or explicit manuscript request.
- Produces: deterministic template selection: V2 by default, V1 only when explicitly selected.

- [ ] Rewrite `Output Profile Selection` so `book_a4` remains the default profile and `template_version: 2` becomes its default template.
- [ ] Put the V2 synthesis sequence before every legacy rule: title → chapter intro → quick reference → preview → preparation → interleaved Step/Tip blocks → real-world use.
- [ ] State that N Steps require exactly N-1 inter-step tips and every Step body has two or three sentences.
- [ ] Move the current `steps`, final `tip`, mandatory `real_world_use_visual`, and `len(steps)+2` rules under a clearly named `Legacy Book A4 V1 Compatibility` section.
- [ ] State that generic prompts never select the legacy section.
- [ ] Run the focused documentation tests and confirm GREEN.

### Task 3: Reorder the schema and image references around the default

**Files:**
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/manuscript-schema.md`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/asset-policy.md`
- Test: `tests/test_documentation_contract.py`

**Interfaces:**
- Consumes: template selector chosen by the skill.
- Produces: a V2-first authoring reference and a separate V1 compatibility appendix.

- [ ] Move the complete `template_version: 2` JSON example to the beginning of the manuscript schema.
- [ ] Include `practice_preparation`, ordered `practice_blocks`, Step body arrays, inter-step tip arrays, and optional `real_world_use_visual` in one complete example.
- [ ] Relabel the current top-level `steps`/`tip` example as `Historical V1 contract`.
- [ ] Put the V2 image formula first: preview + preparation + every Step, with optional real-world-use image.
- [ ] Keep the V1 `len(steps)+2` formula only in the historical compatibility section.
- [ ] Run documentation tests and inspect the rendered Markdown for contradictory unscoped defaults.

### Task 4: Add deterministic template-routing helpers and tests

**Files:**
- Create: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/select_book_template.py`
- Create: `tests/test_book_template_routing.py`

**Interfaces:**
- Produces: `select_template(request_text: str) -> int`.
- Returns: `1` only for an explicit legacy selector; otherwise `2`.

- [ ] Write RED tests for generic Korean requests, next-version requests, explicit V2 requests, and explicit V1/legacy requests.
- [ ] Add tests preventing incidental source text such as `V1 파일을 참고해 새 원고를 만들어줘` from selecting V1 unless the request explicitly asks for the V1 template.
- [ ] Implement a minimal explicit-selector parser with normalized whitespace and a narrow legacy allowlist.
- [ ] Return a deterministic reason code alongside the version if the existing script style favors structured output: `default_v2`, `explicit_v2`, or `explicit_legacy_v1`.
- [ ] Run `python -m unittest tests.test_book_template_routing -v`.
- [ ] Document that the skill must call this helper before allocating a new version.

### Task 5: Preserve V1 compatibility while rejecting unknown versions

**Files:**
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/validate_manuscript.py`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/render_manuscript.py`
- Test: `tests/test_manuscript_v2.py`
- Test: `tests/test_manuscript_renderer.py`

**Interfaces:**
- Consumes: historical V1 without `template_version`, V2 with `template_version: 2`, or an unsupported value.
- Produces: preserved V1 behavior, V2 behavior, or deterministic `unsupported_template_version` failure.

- [ ] Add a RED test that `template_version: 3` is rejected instead of silently falling into V1.
- [ ] Keep missing `template_version` valid only for historical V1 JSON that contains the complete legacy field set.
- [ ] Keep `template_version: 2` routed exclusively through `practice_preparation` and `practice_blocks`.
- [ ] Add a test proving a partial V2 document cannot omit the version and be accepted as V1.
- [ ] Run all V1 and V2 manuscript validator/renderer tests.

### Task 6: Add a synthesis preflight before image generation

**Files:**
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/SKILL.md`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/manuscript-schema.md`
- Test: `tests/test_obsidian_manuscript_workspace.py`

**Interfaces:**
- Consumes: newly allocated manuscript metadata before image generation.
- Produces: a preflight decision that stops generation when the selected contract and JSON shape disagree.

- [ ] Require preflight checks before generating any image: selected template is 2, `template_version` equals 2, preparation exists, practice blocks alternate correctly, and no legacy final `tip` field is present.
- [ ] Define deterministic stop code `book_template_contract_mismatch` for a new package shaped like V1 after V2 was selected.
- [ ] Require the reported completion summary to include `template: book_a4 V2`, independently from immutable version number such as `v0.3`.
- [ ] Add documentation tests for the preflight and completion summary.

### Task 7: Synchronize the installed skill and verify identical behavior

**Files:**
- Source: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/**`
- Installed target: `%USERPROFILE%\\.codex\\skills\\obsidian-manuscript-publisher\\**`
- Test: repository and installed script smoke tests

**Interfaces:**
- Consumes: verified repository skill tree.
- Produces: hash-equal installed files for every file changed by this plan.

- [ ] Copy only verified source files; exclude `__pycache__`, runtime configuration, certificates, API keys, Vault files, and generated manuscripts.
- [ ] Compare SHA-256 for every changed repository/installed file and require equality.
- [ ] Run template-routing and V2 validator smoke tests against the installed scripts.
- [ ] Restart or open a new Codex task so the updated skill instructions are loaded fresh.

### Task 8: Regenerate the affected manuscript as a new immutable version

**Files:**
- Preserve: `01 Manuscript/Part 1-06 학교 품의 기안 스킬/v0.2/**`
- Create through the normal synthesis pipeline: next available immutable version, expected `v0.3`

**Interfaces:**
- Consumes: the same verified material cards used by v0.2.
- Produces: a V2 manuscript with preparation, inter-step tips, V2 visuals, HTML, PDF, validation, publication, and desktop export.

- [ ] Allocate the next version without modifying v0.2.
- [ ] Confirm `manuscript.json` contains `template_version: 2`, `practice_preparation`, and `practice_blocks` and does not contain legacy `steps` or final `tip`.
- [ ] Confirm every Step body has exactly two or three sentences and N Steps have exactly N-1 tips.
- [ ] Confirm required images are preview + preparation + Step 1..N, with optional real-world-use image only when evidence-bearing.
- [ ] Run validation and require `status: ready`.
- [ ] Render HTML/PDF and inspect all pages.
- [ ] Publish through Local REST with byte readback and SHA-256 equality.
- [ ] Export the verified bundle to the desktop publication library.
- [ ] Report immutable version and template version separately: `version: v0.3`, `template: book_a4 V2`.

### Task 9: Final regression and release gate

**Files:**
- Test: complete repository test suite
- Audit: Git diff, installed hashes, secret scan

**Interfaces:**
- Produces: fresh evidence that the default changed without regressing historical data or unrelated profiles.

- [ ] Run V1/V2 manuscript tests, routing tests, documentation tests, publisher tests, desktop exporter tests, archive/delete tests, and adaptive-blog tests.
- [ ] Run Python compilation, PowerShell installer contracts, secret scan, and `git diff --check`.
- [ ] Verify historical v0.2 still validates/renders as V1 when explicitly selected or re-opened.
- [ ] Verify generic new synthesis selects V2 in a fresh Codex task.
- [ ] Confirm no API key, certificate, personal Vault content, generated manuscript, or private path entered the repository diff.
- [ ] Do not commit, tag, push, or publish a GitHub release without separate user authorization.

## Success criteria

- A generic new A4 manuscript request always creates `template_version: 2`.
- An explicit legacy request still creates or reuses the V1 contract without changing historical files.
- Immutable document version and template version are reported as separate values.
- The affected school-procurement manuscript is reissued as a new V2 version; v0.2 remains intact.
- Conversation storage, Obsidian publication, deletion, blog generation, installation, and desktop export retain their existing verified behavior.
