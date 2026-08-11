# Book A4 V2 Interleaved Tips and Realistic Visuals Design

## Status

Design only. No product code, installed skill, Vault, publication library, or Git history is changed by this document.

## Goal

Preserve every existing Obsidian Manuscript Publisher capability while adding a versioned A4 manuscript contract that produces flexible build-oriented Steps, exactly two or three sentences per Step, a topic-specific tip between each pair of Steps, and wide professional AI-generated explanatory visuals.

## Current evidence

- The current `book_a4` contract requires dynamic Steps but noun-phrase titles, one final tip block, and preview/Step/real-world-use visual slots.
- The current renderer and publisher accept `output_profile: book_a4` and inspect the legacy top-level fields directly.
- The current adaptive blog profile has independent schema, validator, renderer, asset policy, and tests and must remain untouched.
- Existing continuity records state that conversation archival, exact-key deletion, Local REST publication, binary readback, immutable versions, and desktop export are already working contracts.
- The new reference PDF places preparation before practice, uses realistic application-oriented visuals, and interleaves tip blocks with practice content.

## Decision

Add a versioned `book_a4_v2` contract rather than replacing the existing `book_a4` contract. The version selector is explicit in `manuscript.json`; the existing `book_a4` path remains the compatibility renderer for historical versions. New synthesis requests use `book_a4_v2` only after the new validator and renderer pass.

## V2 content model

The V2 manuscript keeps the existing chapter-level fields and adds an ordered `practice_blocks` collection:

```json
{
  "output_profile": "book_a4",
  "template_version": 2,
  "practice_blocks": [
    {"type": "step", "number": 1, "title": "", "body": ["", ""], "interaction": {}, "artifact": {}, "visual": {}},
    {"type": "tip", "after_step": 1, "title": "", "body": ["", ""]},
    {"type": "step", "number": 2, "title": "", "body": ["", "", ""], "interaction": {}, "artifact": {}, "visual": {}}
  ]
}
```

The block sequence must be `step(1), tip(1), step(2), ... step(N)`. Therefore every N-step manuscript has exactly N-1 inter-step tips, and no tip is inserted after the last Step. Each Step remains a build action performed through a conversation with the relevant AI agent; finished-tool usage belongs in `[실전 활용하기]`.

## Editorial rules

- A Step body contains exactly two or three Korean sentences.
- The sentences cover request/preparation, agent action/result, and user verification when three sentences are available.
- Step titles may use the approved sample's concise action style; the title rule is separate from sentence-count validation.
- Every tip is specific to the adjacent build decision and contains two or three short sentences or an equivalent two-item structured body.
- `[이번 챕터에서는]`, Step, `[실전 활용하기]`, and each tip remain concise two- or three-sentence paragraphs where the profile requires prose.
- The manuscript does not claim that AI-generated visuals are actual screenshots.

## Visual pipeline

Required V2 slots are one preview visual, one preparation visual, and one visual for every Step. A real-world-use visual is optional and must not be required merely to satisfy a slot formula.

The image pipeline is:

1. Finalize the verified Step meaning and visual kind.
2. Generate a wide landscape base image with Codex built-in image generation.
3. Add deterministic red numbers, arrows, borders, and short verified labels after generation so long Korean text is not left to the image model.
4. Inspect the selected image at original size.
5. Record generation prompt, post-processing metadata, dimensions, hash, quality review, and disclosure in the manifest.

Accepted visual kinds remain `ui_screen`, `work_product`, `workflow_diagram`, `result_preview`, and `field_scene`. Prompts must prohibit generic AI decoration, invented menus, unreadable Korean, and unrelated visual elements. A failed visual blocks publication; it is never replaced with a blank panel.

## Rendering

The V2 HTML and PDF renderers preserve the established A4 portrait page, green section labels, preview/result panel, and immediate image captions. Practice content is emitted in source order: Step heading, two/three-sentence body, wide visual, caption, tip box, then the next Step. CSS and ReportLab grouping must prevent a heading or caption from being separated from its visual when a page break occurs.

## Compatibility boundaries

The following remain unchanged: conversation archive and refresh, material-card structure, exact conversation deletion, REST routes, binary upload/readback, hash validation, immutable version allocation, adaptive blog profile, installation/bootstrap, desktop publication library, and historical `book_a4` output. Shared helper extraction is allowed only when an existing test proves byte-for-byte and behavior compatibility for the old path.

## Failure behavior

- Unsupported template versions fail before rendering or publication.
- A malformed practice block, wrong sentence count, missing inter-step tip, missing visual, invalid image, or stale hash returns deterministic validation errors.
- A V2 validation failure does not alter the last verified Vault or desktop bundle.
- A legacy V1 package continues through its original contract and does not inherit V2 requirements.

## Verification strategy

The implementation must include failing tests for the V2 rules, passing tests for the minimal implementation, legacy fixture regression tests, rendered HTML/PDF order checks, landscape image checks, manifest/hash checks, and a diff audit proving that non-target subsystems did not change.
