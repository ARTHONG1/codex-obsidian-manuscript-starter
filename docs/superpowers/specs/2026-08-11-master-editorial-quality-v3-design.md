# Master Editorial Quality V3 Design

## Purpose

Apply the editorial quality demonstrated by the three approved master manuscripts to every newly synthesized book manuscript and adaptive blog. V3 replaces mechanical development-report prose, rigid Step/tip counts, decorative AI imagery, and repetitive page composition with reader-centered practical writing, master-style AI visuals, and profile-specific publication layouts.

## Non-negotiable decisions

- Every V3 book and blog visual uses `generated_scene` created with Codex built-in image generation. Historical blog packages may retain `provided_asset`.
- Generated visuals must look like polished instructional software, document, settings, result, workflow, or field scenes tied to the actual topic.
- Codex must not add red boxes, numbered callouts, arrows, or other instructional overlays. The user performs those edits later when desired.
- New book manuscripts use `template_version: 3` and preserve historical V1/V2 validation and rendering.
- New blogs use `editorial_quality_version: 3` and preserve historical adaptive-blog packages.
- Existing conversation archives, material cards, Local REST publication, binary readback, immutable versions, deletion, desktop export, and installation behavior remain unchanged.
- Existing immutable documents are never rewritten; regeneration allocates a fresh `v0.N`.

## Architecture

V3 separates editorial synthesis into three contracts:

1. `master editorial profile`: shared voice, information-density, evidence, tip, caption, and visual-quality requirements.
2. `profile schema`: book and blog retain independent structures and renderers.
3. `quality gate`: deterministic structural checks plus explicit editorial and visual attestations. The score is an auditable attestation, not independent proof of semantic correctness.

The synthesis flow is:

```text
active conversation materials
→ editorial brief
→ profile-specific structured content
→ visual briefs
→ AI image generation and original-size inspection
→ profile validation and score
→ render
→ Local REST publication
→ desktop export
```

## Shared master editorial profile

The profile requires natural Korean honorific prose aimed at a teacher completing a practical task. It favors concrete tool names, menu names, inputs, requests, settings, outputs, checks, and cautions over development-internal terms.

Target sentence ranges:

- chapter introduction: 3–5 sentences
- preparation: 2–4 sentences
- each Step: 2–4 sentences
- each tip: 3–5 sentences
- real-world use: 3–5 sentences
- caption: one sentence

Sentence ranges are editorial targets with deterministic boundary checks. A Step may cover preparation, account connection, permissions, external settings, folder setup, a request to Codex, Skill/plugin/MCP creation, execution, verification, correction, installation, or reuse when that action is necessary to complete the chapter outcome.

Step titles may be concise noun phrases or natural action sentences. The exact noun-ending allowlist and the ban on action-sentence titles are removed for V3.

Tips are evidence-driven. There is no N-1 formula. Zero or more tips may follow a Step, but every tip must address a concrete prompt, permission, security, error, distinction, local variation, verification method, or reuse shortcut.

## Book V3 contract

Book V3 retains the fixed editorial section order:

```text
chapter title
[이번 챕터에서는]
[한눈에 보기]
[미리 보기]
[실습 사전 준비]
[실습하기]
Step and tip blocks in source-supported order
[실전 활용하기]
optional final caution
```

`practice_blocks` contains contiguous Step numbers and optional tips associated with the immediately preceding Step. It does not require alternation or a fixed tip count.

The preview visual is required. Preparation and Step visuals are selected by an explicit visual plan. Every Step must be covered by either its own visual or a shared visual whose `covers_steps` lists that Step. A decorative field scene cannot satisfy Step coverage.

The A4 portrait renderer uses adaptive flow. It may place two short Steps on one page, keep a complex image and its tip together, and move a complete block when splitting would create an orphan. It does not force one Step per page.

## Blog V3 contract

Blog V3 keeps portable Markdown and semantic HTML. It uses the same master voice and practical evidence but rewrites the material as a platform-independent article rather than copying book sections.

The article chooses one supported mode and uses five to seven sections. Each section must have a distinct editorial purpose and an evidence-backed practical contribution. The hero is required; zero to four section visuals are allowed only when they improve understanding. Every V3 blog visual uses `generated_scene`.

## AI visual direction

Every generated visual carries a `visual_brief` with:

```json
{
  "purpose": "what this image teaches",
  "screen_state": "the exact state or result to depict",
  "visible_elements": ["verified element"],
  "reader_check": "what the reader confirms",
  "covers_steps": [1],
  "style": "professional Korean practical-book editorial visual",
  "forbidden_overlays": ["red_box", "numbered_callout", "arrow"]
}
```

The generation prompt must request a professional, realistic instructional visual and prohibit generic AI decoration, invented irrelevant controls, unreadable Korean prose, red boxes, numbered callouts, and arrows. A visual can use short verified labels; long Korean passages remain in the document renderer.

Original-size review requires purpose match, artifact specificity, professional composition, legible content, no generation artifacts, no generic AI motifs, and no instructional overlays. Codex revises a failed visual prompt up to three total generation attempts. A third failure returns `image_generation_failed` and blocks publication.

## Editorial quality gate

The validator calculates a 100-point attested score:

- reader problem and outcome clarity: 15
- complete practical sequence: 20
- master voice: 15
- Step information density: 15
- tip usefulness: 10
- AI visual quality: 15
- layout and rhythm review: 10

Publication requires at least 85 points and no hard failure. Hard failures include unsupported claims, missing required output, uncovered Step, failed visual review, an instructional overlay, unreadable visual, stale validation, or an invalid asset hash.

## Compatibility and safety

- V1 and V2 keep their existing validators and renderers.
- V3 is the default only for newly synthesized content.
- Publication and desktop export accept V3 only after fresh validation and rendering.
- No API key, certificate, private attachment, generated manuscript, or personal Vault path enters the repository.
- The feature does not modify archive/delete behavior or add filesystem fallback writes to the Vault.

## Acceptance criteria

- Three master-derived, non-copyright fixture chapters demonstrate procurement, news briefing, and calendar automation structures.
- New book output uses 3–5 sentence introductions, 2–4 sentence Steps, evidence-driven tips, and master-style AI visuals without overlays.
- New blog output uses the same voice and visual quality while retaining portable Markdown and HTML.
- Historical V1/V2 book packages and historical blogs still validate, render, publish, and export.
- Full Python, PowerShell contract, secret-scan, render, publication, archive, delete, and desktop-export tests pass.
