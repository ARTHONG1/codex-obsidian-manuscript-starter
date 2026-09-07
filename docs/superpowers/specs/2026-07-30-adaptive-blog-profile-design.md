# Adaptive Blog Output Profile Design

## Goal

Add a platform-independent `adaptive_blog` output profile to Obsidian Manuscript Publisher. The profile converts the same verified conversation materials used by `book_a4` into portable Markdown and semantic HTML without changing the existing A4 manuscript workflow.

## User Intent

The user is not asking for another tone preset inside the book template. The blog output must have its own editorial structure, validation rules, image policy, files, and Vault destination. It should read like a careful human practitioner wrote it, without copying any living writer's distinctive wording or pretending that the model personally experienced events.

## Compatibility Boundary

- `book_a4` remains the default when no output profile is named.
- Existing manuscript JSON, validator, renderer, paths, image count, versioning, and tests stay unchanged.
- Conversation archive, material cards, exact `conversation_key`, deletion, Local REST publication, and immutable `v0.N` rules are shared.
- Blog versions publish below `02 Blog/<topic-slug>/v0.N`; book versions stay below `01 Manuscript`.
- One source conversation may produce either profile or both profiles as independent immutable versions.

## Profile Selection

Natural-language triggers map to explicit profile IDs:

- `출판 원고형`, `A4 원고`, or no profile: `book_a4`
- `범용 블로그형`, `블로그 버전`, `Markdown과 HTML 블로그`: `adaptive_blog`
- `둘 다`: run two independent synthesis pipelines; one failure must not overwrite or relabel the other output.

The generated JSON always records `output_profile`. A renderer or validator refuses a payload for another profile.

## Adaptive Editorial Modes

The synthesis pass chooses one mode from the evidence, then records why in `mode_reason`.

### `practical_guide`

Use for technology building, repeatable work, and how-to material. The semantic flow must cover a concrete problem, the working principle, an actionable method, a verified result or failure correction, and reader application. Headings remain topic-specific; the five required roles appear in canonical order and one role may repeat contiguously when a rich topic needs six or seven sections.

### `case_story`

Use when the source contains a meaningful before state, decision, attempt, correction, and observed result. The semantic flow must cover before, turning point, process, result, and lesson. It must not invent personal experience absent from the source.

### `insight_column`

Use for a focused interpretation or educational argument. The semantic flow must cover an observation, contrast, principle, grounded example, and closing implication. It must not pad a short insight into a fake tutorial.

## Blog Data Contract

`blog.json` contains:

- `output_profile: adaptive_blog`
- `mode` and non-empty `mode_reason`
- `title`, `slug`, `audience`, `dek`, `lead`, and `core_idea`
- `sections`: five to seven ordered sections
- `evidence_points`: at least two source-grounded details
- `next_action`, `closing`, `tags`, and `meta_description`
- `hero_visual`: exactly one required hero image
- optional `section.visual` values for evidence-carrying images
- `humanity_review`: six true checks and a concrete review note

Each section has a free editorial `heading`, exactly one semantic `role`, one or more plain paragraph blocks, `evidence_refs`, and an optional visual. The five required mode roles all appear in canonical order. A role may repeat only in a contiguous run, allowing six or seven sections without introducing a supporting or unknown role. Headings are not fixed template labels, and paragraph counts may vary by section. Blog v1 does not accept raw Markdown lists or fenced code blocks in `paragraphs`.

Every evidence point has a unique `evidence_id` and records `kind`, `detail`, one or more `source_refs`, and `verification`. Accepted kinds are `artifact`, `error`, `result`, `comparison`, `decision`, and `observation`. `lead_evidence_refs` and every section's `evidence_refs` must resolve to those IDs.

## Human Editorial Contract

The output must demonstrate all of these traits:

1. A source-grounded opening: scene, problem, question, contrast, or observed result.
2. One central idea carried from lead through closing.
3. At least two concrete evidence points such as a file, command, error, result, comparison, or decision.
4. Visible judgment: explain why a choice was made, what failed, what was checked, or where a limit remains.
5. Uneven but deliberate rhythm: section paragraph counts must not all be identical when there are three or more sections.
6. No fabricated first-person experience.

The validator rejects canned phrases including `안녕하세요`, `오늘은 ~ 알아보겠습니다`, `결론적으로`, `도움이 되었기를 바랍니다`, and `지금까지 ~ 알아보았습니다`. It also rejects clickbait terms such as `완벽한`, `혁신적인`, `단 몇 분 만에`, `무조건`, `100%`, and `한 번에 끝` in the title.

First-person experience markers such as `저는`, `제가`, `직접 해보니`, or `느꼈습니다` require `first_person_evidence_refs`, and every referenced ID must resolve to an `observation` evidence point with a source reference and verification. Otherwise validation fails. The preferred default is neutral practitioner prose.

## Visual Contract

- One hero visual is required.
- Zero to four section visuals are allowed; a visual is added only where it explains an artifact, workflow, comparison, result, or real use.
- Supported methods are `provided_asset` and `generated_scene`.
- Every image is PNG or JPEG, at least 1200 px wide, and at least 1.5:1 landscape.
- Every visual has a unique `asset_id`, meaningful `alt_text`, caption, evidence kind, visual kind, privacy status, and complete quality review.
- Generated visuals retain the existing professional editorial prompt and anti-AI-motif checks. Their visual metadata and manifest record both carry the exact internal disclosure `AI 생성 설명 이미지`. Public prose, alt text, and captions may describe what the image explains but may not claim it is an actual screenshot.
- Provided assets require source provenance and the same byte, hash, privacy, and quality checks.
- The blog profile does not inherit the book rule `len(steps) + 2`.

## Outputs

Each immutable blog version contains:

```text
v0.N/
├── blog.md
├── blog.html
├── blog.json
├── asset-manifest.json
├── blog-validation.json
├── publication-validation.json
└── assets/
```

Markdown uses portable headings, paragraph blocks, relative image links, captions, and alt text. HTML uses semantic `article`, `header`, `section`, `figure`, and `footer` elements with restrained embedded preview CSS and no platform scripts or tracking. Blog v1 deliberately excludes raw Markdown list and code blocks from the JSON content model.

## Rendering Rules

- The renderer accepts only a ready `adaptive_blog` package.
- It does not expose internal fields such as `mode_reason`, `source_refs`, or `humanity_review` in public prose.
- It preserves intentional paragraph boundaries and never inserts generic introductory or closing copy.
- It renders paragraph blocks as text; it does not interpret user-supplied Markdown or raw HTML.
- It renders section visuals directly after the section content they support.
- It writes Markdown and HTML atomically into the supplied version directory.

## Publication and Failure Handling

- Reuse the existing byte-verified generic version publisher.
- Validation must return `status: ready` before rendering or publication.
- A failed blog validation does not mutate the last verified blog version or any book version.
- Missing evidence, canned prose, fabricated first-person experience, invalid visuals, duplicate assets, path escape, or hash mismatch return deterministic error codes.
- Obsidian being closed remains a publication failure; no direct filesystem fallback is allowed.

## Tests

The test suite must prove:

- valid packages render both Markdown and HTML;
- all three editorial modes accept five to seven singular-role sections in canonical order, with only contiguous role repetition;
- evidence IDs are unique and every lead, section, and first-person reference resolves to an allowed evidence record;
- profile mismatch, canned phrases, clickbait titles, unsupported first-person experience, uniform section rhythm, insufficient evidence, duplicate assets, missing alt text, invalid image dimensions, path escape, and hash mismatch fail;
- one hero with no section image succeeds;
- provided and generated visual methods both succeed when valid;
- existing `book_a4` tests remain unchanged and pass;
- installer, secret scan, archive, deletion, and REST publication behavior do not regress.

## Documentation and User Commands

README and skill metadata expose these requests:

```text
이 대화 재료로 플랫폼 독립 범용 블로그형을 만들어줘.
이 재료를 출판 원고형과 범용 블로그형으로 각각 만들어줘.
```

The completion response names the selected mode, generated paths, evidence count, image count, validation status, and publication status. It never claims that an AI detector was defeated or that the writing is guaranteed to be indistinguishable from a person.
