# Adaptive Blog Output Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a profile-selected, source-grounded blog pipeline that emits portable Markdown and HTML while preserving the current A4 manuscript workflow unchanged.

**Architecture:** Keep conversation capture and byte-verified publication shared. Add independent blog schema, validator, and renderer modules selected by `output_profile: adaptive_blog`; route natural-language requests in the existing publisher skill and store blog versions under `02 Blog`.

**Tech Stack:** Python 3.12 standard library, Pillow, unittest, semantic HTML5, Markdown, existing Obsidian Local REST publisher, PowerShell/Pester release tests.

## Global Constraints

- `book_a4` remains the default and its current scripts and tests must stay green.
- Blog output is `blog.md` plus `blog.html`; no blog PDF is generated.
- Blog modes are exactly `practical_guide`, `case_story`, and `insight_column`.
- Hero image count is exactly one; section images are zero to four.
- Images are PNG/JPEG, width at least 1200 px, ratio at least 1.5, version-local, and SHA-256 verified.
- Vault publication uses HTTPS Local REST with byte readback; no direct filesystem fallback.
- No external image API, API key, platform SDK, tracking script, or new runtime dependency.
- Do not imitate a named writer's distinctive voice or fabricate first-person experience.

---

### Task 1: Executable Blog Contract

**Files:**
- Create: `tests/test_blog_renderer.py`
- Create: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/blog-schema.md`
- Create: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/blog-editorial-policy.md`

**Interfaces:**
- Consumes: the approved design specification.
- Produces: literal fixtures and expected error codes used by all later tasks.

- [x] Write a valid package fixture with profile, mode, mode reason, title metadata, five varied sections, two evidence points, a hero visual, optional section visual, and humanity review.
- [x] Add tests for each accepted mode and its required semantic roles.
- [x] Add failing tests for profile mismatch, missing evidence, canned phrases, clickbait title, unsupported first person, uniform rhythm, missing alt text, duplicate asset IDs, path escape, hash mismatch, portrait image, and low resolution.
- [x] Run `python -m unittest tests.test_blog_renderer -v` and confirm failure because `validate_blog.py` and `render_blog.py` do not exist.
- [x] Write the two reference contracts using the exact tested field names and error conditions.

### Task 2: Deterministic Blog Validator

**Files:**
- Create: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/validate_blog.py`
- Modify: `tests/test_blog_renderer.py`

**Interfaces:**
- Consumes: `validate_package(blog: dict, manifest: dict, version_dir: Path) -> dict` contract from tests.
- Produces: CLI `validate_blog.py BLOG_JSON ASSET_MANIFEST OUTPUT_REPORT` and deterministic `{status, errors, warnings}` JSON.

- [x] Implement structural checks for `output_profile`, mode, required roles, sections, evidence, metadata, and humanity review.
- [x] Implement human editorial checks for banned openings/closings, clickbait, grounded first person, central-idea presence, concrete evidence, and varied section rhythm.
- [x] Implement visual and manifest checks for supported methods, unique IDs, alt text, provenance, prompt policy, version-local paths, signatures, dimensions, and SHA-256.
- [x] Run `python -m unittest tests.test_blog_renderer.BlogValidatorTests -v`; fix production code until all validator tests pass.
- [ ] Run existing manuscript tests and confirm the independent validator caused no regression.

### Task 3: Portable Markdown and HTML Renderer

**Files:**
- Create: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/render_blog.py`
- Modify: `tests/test_blog_renderer.py`

**Interfaces:**
- Consumes: a blog package that `validate_blog.py` reports as ready.
- Produces: `render_blog.py BLOG_JSON OUTPUT_DIRECTORY`, `blog.md`, and `blog.html`.

- [x] Add tests asserting portable Markdown headings, relative image links, alt text, immediate captions, semantic HTML elements, no tracking scripts, and no internal review metadata.
- [x] Run the renderer tests and confirm failure because output files are absent.
- [x] Implement paragraph-preserving Markdown and escaped semantic HTML rendering with restrained embedded CSS.
- [x] Require the hero image and validate any optional section visuals before writing either output.
- [x] Write both outputs through temporary sibling files and restore prior outputs if either replacement fails.
- [ ] Run all blog renderer tests and the existing manuscript tests.

### Task 4: Skill Routing and Publication Workflow

**Files:**
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/SKILL.md`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/agents/openai.yaml`
- Modify: `tests/test_obsidian_manuscript_workspace.py`

**Interfaces:**
- Consumes: blog reference files and executable scripts.
- Produces: unambiguous profile selection, synthesis order, Vault path, completion response, and dual-output behavior.

- [ ] Add behavioral contract tests that a user request naming a blog profile selects `adaptive_blog`, while an unspecified request retains `book_a4`.
- [ ] Record a baseline failure against the current skill routing.
- [ ] Add a concise Output Profile Selection section that routes blog synthesis to `02 Blog/<topic-slug>/v0.N` and book synthesis to the existing path.
- [ ] Add the source-grounded synthesis sequence: choose mode, write JSON and assets, validate, render, publish, and report.
- [ ] Link blog-specific reference files only from the blog branch so book tasks do not load them.
- [ ] Update UI metadata to mention A4 and portable blog outputs without changing setup behavior.
- [ ] Run workspace contract tests and both renderer suites.

### Task 5: Public Documentation and Release Metadata

**Files:**
- Modify: `README.md`
- Modify: `plugins/obsidian-manuscript-publisher/.codex-plugin/plugin.json`
- Modify: `.agents/plugins/marketplace.json` only if its schema exposes plugin version metadata.

**Interfaces:**
- Consumes: final commands and output names from Task 4.
- Produces: beginner-facing usage examples and versioned public metadata.

- [ ] Document the distinction between `book_a4` and `adaptive_blog`, the three blog modes, Markdown/HTML outputs, and two natural-language request examples.
- [ ] State that the system avoids canned AI patterns but does not promise to defeat AI detectors.
- [ ] Bump the plugin minor version from `0.1.0` to `0.2.0`.
- [ ] Run secret and installer Pester tests.

### Task 6: Personal Installation Sync and Full Verification

**Files:**
- Sync source: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/**`
- Sync destination: `%USERPROFILE%\.codex\skills\obsidian-manuscript-publisher\**`
- Update: `.planning/obsidian-manuscript-continuity/{task_plan.md,findings.md,progress.md,history.md}`

**Interfaces:**
- Consumes: verified repository skill tree.
- Produces: matching personal installation and persistent continuity record.

- [ ] Run all Python tests and require zero failures.
- [ ] Run `InstallerContract.Tests.ps1` and `SecretScan.Tests.ps1`; require zero failures.
- [ ] Generate a realistic `practical_guide` fixture and render Markdown/HTML.
- [ ] Inspect rendered HTML at desktop and narrow widths; verify images, text, headings, and captions do not overlap.
- [ ] Copy only verified skill files into the personal skill directory, preserving no `__pycache__` files.
- [ ] Compare SHA-256 for every repository and installed skill file; require full equality.
- [ ] Re-run the full Python suite against the repository and a smoke validation against the installed scripts.
- [ ] Record exact test counts, file hashes, and remaining limitations in the active planning files.
