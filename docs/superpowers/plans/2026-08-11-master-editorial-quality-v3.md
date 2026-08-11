# Master Editorial Quality V3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every newly synthesized book manuscript and adaptive blog match the approved master manuscripts in voice, practical depth, AI visual quality, and publication layout while preserving all existing storage and publication safety contracts.

**Architecture:** Add one shared master editorial profile and shared deterministic quality helpers, then add independent Book V3 and Blog V3 schema/validator/renderer branches. New synthesis routes to V3; historical Book V1/V2 and blog packages retain their existing branches and immutable behavior.

**Tech Stack:** Codex skill Markdown, Python 3, unittest, JSON contracts, Pillow, ReportLab, HTML/CSS, existing Local REST publisher and desktop exporter.

## Global Constraints

- Do not add red boxes, numbered callouts, arrows, or other instructional overlays to generated images.
- Every V3 book and blog visual uses `generated_scene` from Codex built-in image generation and must resemble a polished instructional software, document, settings, result, workflow, or field scene tied to the topic.
- New books use `template_version: 3`; historical V1/V2 remain readable and immutable.
- New blogs use `editorial_quality_version: 3`; historical blog packages remain readable and immutable.
- Preserve conversation archive, material card, Local REST, byte readback, SHA-256, deletion, desktop export, installer, and secret-handling behavior.
- Never overwrite an existing `v0.N`; corrected output always receives the next immutable version.
- A score below 85 or any hard quality failure blocks render and publication.
- Do not commit, tag, push, or publish a release without separate user authorization.

---

### Task 1: Lock the shared master editorial contract

**Files:**
- Create: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/master-editorial-profile.md`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/SKILL.md`
- Modify: `tests/test_documentation_contract.py`

**Interfaces:**
- Consumes: approved V3 design and master-analysis findings.
- Produces: one normative profile referenced by book and blog synthesis.

- [ ] Add failing documentation tests asserting the shared profile contains the exact sentence targets, evidence-driven tip rule, flexible Step title rule, 85-point threshold, and the overlay prohibition.
- [ ] Run `python -m unittest tests.test_documentation_contract -v` and confirm failures identify the missing V3 contract.
- [ ] Create `master-editorial-profile.md` with the approved voice, section lengths, Step types, tip criteria, visual brief, score table, and hard failures.
- [ ] Update `SKILL.md` so both book and blog synthesis must read the shared profile before writing structured content.
- [ ] Remove V3-facing instructions that require noun-only Step titles, exact N-1 tips, or automatic post-processing overlays; keep those statements explicitly scoped to historical branches where required.
- [ ] Re-run `python -m unittest tests.test_documentation_contract -v` and require all tests to pass.

### Task 2: Route all new synthesis to V3 without breaking history

**Files:**
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/select_book_template.py`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/SKILL.md`
- Modify: `tests/test_book_template_routing.py`
- Modify: `tests/test_obsidian_manuscript_workspace.py`

**Interfaces:**
- Consumes: `select_book_template(request_text, requested_template_version)`.
- Produces: `{output_profile: "book_a4", template_version: 3, reason: "default_new_book_a4"}` for generic new-book requests.

- [ ] Change routing tests so generic book requests and next-version requests expect V3.
- [ ] Add tests proving explicit `V1`, `레거시`, and explicit V2 requests retain their selected historical contract.
- [ ] Add a test rejecting template versions outside `{1, 2, 3}`.
- [ ] Run `python -m unittest tests.test_book_template_routing -v` and confirm the current V2 default fails.
- [ ] Extend `select_book_template()` to return V3 by default and explicit V2 only when the request unambiguously names V2.
- [ ] Add `assert_new_book_a4_contract()` checks for `template_version: 3`, `editorial_quality_version: 3`, V3 `practice_blocks`, and `editorial_review`.
- [ ] Re-run routing and workspace tests and require all to pass.

### Task 3: Implement shared editorial-quality helpers

**Files:**
- Create: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/editorial_quality.py`
- Create: `tests/test_editorial_quality_v3.py`

**Interfaces:**
- Produces: `sentence_count(value: object) -> int`.
- Produces: `validate_sentence_range(value: object, minimum: int, maximum: int, code: str) -> list[dict]`.
- Produces: `validate_master_voice(public_text: str) -> list[dict]`.
- Produces: `validate_visual_brief(brief: object, *, asset_id: str) -> list[dict]`.
- Produces: `compute_editorial_score(review: object) -> tuple[int, list[dict]]`.

- [ ] Write failing tests for Korean sentence counting, 3–5 sentence introductions, 2–4 sentence Steps, 3–5 sentence tips, repetitive report-style wording, missing visual-brief fields, forbidden overlays, and scores below 85.
- [ ] Run `python -m unittest tests.test_editorial_quality_v3 -v` and confirm import failure for the missing module.
- [ ] Implement sentence-range validation without treating decimals, URLs, or abbreviations as sentence boundaries.
- [ ] Implement conservative master-voice checks for repeated development-report endings and unsupported promotional absolutes; return stable error codes rather than rewriting prose.
- [ ] Implement `validate_visual_brief()` requiring `purpose`, `screen_state`, non-empty `visible_elements`, `reader_check`, `style`, and exact `forbidden_overlays` containing `red_box`, `numbered_callout`, and `arrow`.
- [ ] Implement score validation for the seven approved categories, exact maximum weights totaling 100, a minimum total of 85, and boolean hard-failure attestations.
- [ ] Run the new test module and require all tests to pass.

### Task 4: Add the Book V3 schema and validator branch

**Files:**
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/manuscript-schema.md`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/validate_manuscript.py`
- Create: `tests/test_manuscript_v3.py`
- Preserve: `tests/test_manuscript_v2.py`
- Preserve: `tests/test_manuscript_renderer.py`

**Interfaces:**
- Consumes: `editorial_quality.py` helpers.
- Produces: `_validate_v3_package(manuscript: dict, manifest: dict, version_dir: Path) -> dict`.

- [ ] Add a V3 fixture with `template_version: 3`, `editorial_quality_version: 3`, 3–5 sentence introduction, 2–4 sentence preparation, flexible Step/tip blocks, visual coverage, and a passing editorial review.
- [ ] Add failing tests proving V3 accepts action-sentence or noun-phrase Step titles, accepts zero or multiple tips after a Step, and rejects noncontiguous Step numbering.
- [ ] Add failing tests for a one-sentence Step, a six-sentence tip, uncovered Steps, failed visual review, forbidden overlays, missing score categories, and total score 84.
- [ ] Run `python -m unittest tests.test_manuscript_v3 -v` and confirm the missing V3 branch causes the expected failures.
- [ ] Document the complete Book V3 JSON contract, including `step_kind`, optional `visual`, shared `covers_steps`, `visual_brief`, and `editorial_review`.
- [ ] Implement `_validate_v3_package()` and route only `template_version == 3` to it; leave V1 and V2 code paths unchanged.
- [ ] Require Step coverage by the union of every visual's `covers_steps`; reject a decorative field scene as sole Step coverage.
- [ ] Return stable V3 errors including `v3_editorial_profile_required`, `step_sentence_range_invalid`, `tip_sentence_range_invalid`, `step_visual_coverage_missing`, `instructional_overlay_forbidden`, and `editorial_score_below_threshold`.
- [ ] Run V3, V2, and legacy renderer tests together and require all to pass.

### Task 5: Upgrade the Book V3 AI visual contract

**Files:**
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/asset-policy.md`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/validate_manuscript.py`
- Modify: `tests/test_manuscript_v3.py`

**Interfaces:**
- Consumes: V3 `visual_brief`, manifest `prompt`, dimensions, hash, and `quality_review`.
- Produces: validated master-style generated assets with no instructional overlays.

- [ ] Add failing tests requiring every V3 prompt to describe the topic-specific artifact or screen state and explicitly prohibit red boxes, numbered callouts, and arrows.
- [ ] Add failing tests rejecting generic laptop poses, robot motifs, futuristic dashboards, unreadable Korean prose requests, code-wall imagery, and unrelated charts.
- [ ] Add passing tests for a realistic settings screen, a result preview, a document workflow, and a restrained field scene with short verified labels.
- [ ] Run `python -m unittest tests.test_manuscript_v3 -v` and confirm prompt/brief tests fail under the current asset policy.
- [ ] Rewrite the V3 section of `asset-policy.md` around five visual roles: `workflow_preview`, `preparation_scene`, `instructional_screen`, `result_preview`, and `field_application`.
- [ ] Extend visual review flags with `artifact_specific`, `screen_or_result_plausible`, `print_legible`, and `no_instructional_overlays` while preserving historical review fields.
- [ ] Enforce maximum three generation attempts in `SKILL.md`; the third failed review reports `image_generation_failed` and blocks render.
- [ ] Re-run V3 visual tests and the complete legacy visual suite.

### Task 6: Build adaptive Book V3 HTML and PDF layouts

**Files:**
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/render_manuscript.py`
- Modify: `tests/test_manuscript_v3.py`
- Modify: `tests/test_manuscript_renderer.py`

**Interfaces:**
- Produces: `render_v3_html(data: dict, json_path: Path, output_directory: Path) -> str`.
- Produces: `render_v3_pdf(data: dict, json_path: Path, output_path: Path) -> None`.

- [ ] Add failing tests for the fixed section order, flexible tips, optional Step visuals, shared visual coverage, immediate captions, and no overlay markup.
- [ ] Add a deterministic PDF test confirming identical input produces byte-identical output and V3 does not alter V1/V2 rendering.
- [ ] Add layout tests requiring an introduction/table first page, preview/preparation flow, KeepTogether for image/caption, and no standalone final heading.
- [ ] Run V3 renderer tests and confirm the missing renderer branch fails.
- [ ] Implement `render_v3_html()` with master-style hierarchy, responsive images, readable captions, and content-driven block flow.
- [ ] Implement `render_v3_pdf()` on A4 portrait with 11pt body, 18pt chapter title, green section labels, bordered intro/tip boxes, and adaptive `KeepTogether` blocks.
- [ ] Keep short adjacent Steps together when they fit; move a complete image-caption-tip unit when splitting would orphan its heading or caption.
- [ ] Re-run V3, V2, deterministic PDF, stale-validation, and visual-path tests.

### Task 7: Add Blog V3 editorial and visual quality

**Files:**
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/blog-schema.md`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/blog-editorial-policy.md`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/validate_blog.py`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/render_blog.py`
- Create: `tests/test_blog_editorial_v3.py`
- Preserve: `tests/test_blog_renderer.py`

**Interfaces:**
- Consumes: shared editorial helpers and existing `practical_guide`, `case_story`, or `insight_column` mode.
- Produces: portable V3 `blog.md` and `blog.html` with master voice and master-style generated visuals.

- [ ] Add a V3 blog fixture with `editorial_quality_version: 3`, five to seven purposeful sections, a `generated_scene` hero visual brief, optional generated section visuals, and a passing editorial review.
- [ ] Add failing tests for thin sections, repetitive section rhythm, development-report tone, decorative visuals, overlay instructions, a score below 85, and copied book section labels.
- [ ] Run `python -m unittest tests.test_blog_editorial_v3 -v` and confirm the current validator lacks the V3 requirements.
- [ ] Document V3 blog voice, section purpose, practical depth, and AI visual rules while preserving portable Markdown and semantic HTML.
- [ ] Route `editorial_quality_version == 3` through shared voice, visual-brief, score, hard-failure validation, and a `generated_scene`-only V3 image contract; preserve historical blog validation including `provided_asset`.
- [ ] Update Markdown and HTML rendering only where required for V3 section rhythm and master-style image/caption placement; retain relative image links and escaped untrusted content.
- [ ] Run new blog V3 tests plus the complete existing blog suite.

### Task 8: Make publication and desktop export V3-aware

**Files:**
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/publish_manuscript_version.py`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/export_publication_bundle.py`
- Modify: `tests/test_publish_manuscript_version.py`
- Modify: `tests/test_desktop_publication_export.py`

**Interfaces:**
- Consumes: freshly validated and rendered V3 book/blog packages.
- Produces: unchanged immutable publication and copy-ready desktop bundles.

- [ ] Add failing publication tests for a valid Book V3 package, a valid Blog V3 package, stale editorial validation, an uncovered Step, and a score below 85.
- [ ] Add failing export tests verifying V3 Step/tip order, visual coverage order, captions, and profile/version metadata.
- [ ] Run the publication and export test modules and confirm V3 packages are not yet accepted.
- [ ] Extend package inspection to recognize V3 without weakening the exact file allowlist, byte snapshots, SHA-256 equality, path safety, or remote non-destructive failure behavior.
- [ ] Update book copy text and image insertion order for flexible tips and shared visuals; update blog copy text only for V3 metadata.
- [ ] Re-run publication, export, archive, delete, Local REST security, and path-boundary tests.

### Task 9: Add three master-derived quality fixtures and visual QA

**Files:**
- Create: `tests/fixtures/editorial-v3/procurement.json`
- Create: `tests/fixtures/editorial-v3/news-briefing.json`
- Create: `tests/fixtures/editorial-v3/calendar.json`
- Create: `tests/test_master_editorial_fixtures.py`
- Create: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/render_quality_samples.py`

**Interfaces:**
- Produces: synthetic, non-copyright fixtures that exercise the approved structural patterns without copying master prose or images.

- [ ] Write failing tests that load all three fixtures and require V3 validation, distinct tip counts, flexible Step prose, visual briefs without overlays, and scores of at least 85.
- [ ] Run `python -m unittest tests.test_master_editorial_fixtures -v` and confirm fixtures or V3 behavior are missing.
- [ ] Create the three JSON fixtures with generated placeholder test images produced at runtime, not committed master assets.
- [ ] Implement `render_quality_samples.py --output <directory>` to validate and render each fixture into reviewable HTML/PDF without publishing to the Vault.
- [ ] Render all sample pages, convert PDFs to PNG with bundled Poppler, and visually inspect every page for clipping, unreadable text, repetitive composition, excessive whitespace, and image-caption separation.
- [ ] Record visual-review results in a local QA report excluded from Git; correct renderer defects and rerun until all pages pass.

### Task 10: Update user guidance and installed skill

**Files:**
- Modify: `README.md`
- Modify: `plugins/obsidian-manuscript-publisher/.codex-plugin/plugin.json`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/agents/openai.yaml`
- Sync after tests: `%USERPROFILE%\\.codex\\skills\\obsidian-manuscript-publisher`

**Interfaces:**
- Produces: beginner-facing V3 commands and a tested installed runtime copy.

- [ ] Add documentation tests requiring README examples for a new V3 book, a new V3 blog, master-style AI image generation, and the no-overlay rule.
- [ ] Update README without changing the beginner installation flow or exposing local paths, API keys, or private Vault data.
- [ ] Update plugin metadata only after the V3 contract and tests are green; choose the next semantic version from the current manifest.
- [ ] Run all Python tests with `python -m unittest discover -s tests -p "test_*.py"`.
- [ ] Run PowerShell installer contracts and secret scans using the commands documented in README.
- [ ] Run `python -m compileall` on plugin scripts and `git diff --check`.
- [ ] Copy the verified plugin skill directory to the installed skill location and compare SHA-256 for every synchronized file.
- [ ] In a fresh Codex task, verify a generic book request routes to Book V3 and a blog request routes to Blog V3.
- [ ] Do not regenerate, publish, commit, tag, push, or release until the user separately authorizes those actions.

## Final verification matrix

- New Book V3: validate → render HTML/PDF → visual review → publish simulation → desktop export simulation.
- New Blog V3: validate → render Markdown/HTML → visual review → publish simulation → desktop export simulation.
- Historical Book V1/V2: validate and render unchanged.
- Historical blog: validate and render unchanged.
- Archive/delete/REST/security/installer: complete regression suite.
- Master-quality fixtures: three distinct structures, different tip counts, no automatic overlays, score ≥85.

## Completion criteria

- Generic new book and blog synthesis use V3 by default.
- Text matches the master voice and approved sentence-density targets.
- AI visuals are topic-specific, plausible, print-legible, and free of automatic red boxes, numbered callouts, and arrows.
- Tips are evidence-driven rather than formula-driven.
- A4 and blog layouts no longer repeat one mechanical block pattern.
- Existing immutable outputs and all storage/publication safety guarantees remain intact.
