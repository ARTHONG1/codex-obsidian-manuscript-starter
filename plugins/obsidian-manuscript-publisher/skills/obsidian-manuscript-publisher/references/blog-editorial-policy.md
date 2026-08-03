# Adaptive Blog Editorial Policy

Write the `adaptive_blog` profile as a source-grounded article by a careful practitioner. Do not pour book-template content into a blog layout, imitate a named living writer's distinctive voice, invent personal experience, or claim that the result defeats AI detection.

## Editorial Sequence

1. Read the verified conversation materials and identify the audience, concrete problem, central idea, evidence, choices, limits, and useful next action.
2. Select one editorial mode from the source evidence and record the reason in `mode_reason`; do not display that reason in the finished article.
3. Build a source-grounded lead, five to seven topic-specific sections, and a closing around one `core_idea`.
4. Record at least two concrete `evidence_points` with unique IDs. Link the lead and every section to those IDs, and make the writer's judgment visible through choices, checks, corrections, or limits.
5. Choose one required hero visual and only the section visuals that carry evidence or materially improve understanding.
6. Complete `humanity_review` as a manual editorial attestation after inspecting the actual draft and cited material, validate the package, and render only when validation reports `status: ready`.

The validator enforces deterministic structure, reference resolution, wording, and asset rules, but it does not independently prove semantic source grounding. Codex must compare every cited turn, attachment, or file with the claim it supports before signing the manual editorial attestation or publishing the article.

## Mode Selection

### `practical_guide`

Use for technology building, repeatable work, and how-to material. The article must cover these semantic roles:

`problem` → `principle` → `method` → `evidence` → `application`

Show the concrete problem, the principle that governs the work, an actionable method, a verified result or failure correction, and how the reader can apply it. Do not turn every article into a fixed numbered tutorial; headings and section counts remain specific to the subject.

### `case_story`

Use when the source records a meaningful before state, decision, attempt, correction, and observed result. The article must cover:

`before` → `turning_point` → `process` → `result` → `lesson`

Keep the chronology and the reason for each decision visible. Do not manufacture a personal anecdote, emotion, or success that is absent from the source.

### `insight_column`

Use for a focused interpretation or educational argument. The article must cover:

`observation` → `contrast` → `principle` → `example` → `implication`

Develop one insight through a grounded example and a useful implication. Do not pad a short observation into a false tutorial or force it into a production narrative.

Every mode uses five required roles in the order shown above. Each section has one singular `role` and must not include the legacy plural `roles` field. When the source needs six or seven sections, repeat a substantial role only in adjacent sections before advancing to the next role. Never add `supporting`, return to an earlier role, or invent another role.

## Human Editorial Contract

Every article demonstrates all six qualities below. Record each as `true` only after checking the actual draft and add a concrete `review_note`.

| `humanity_review` field | Required evidence in the draft |
|---|---|
| `source_grounded_opening` | The lead begins with a sourced scene, problem, question, contrast, or observed result. |
| `central_idea_consistency` | The lead, sections, next action, and closing carry one central idea; natural paraphrase is allowed, so literal `core_idea` repetition is not required. |
| `concrete_evidence` | At least two files, commands, errors, results, comparisons, decisions, or observations are traceable to sources. |
| `visible_judgment` | The draft explains why a choice was made, what failed, what was checked, or where a limit remains. |
| `varied_rhythm` | With three or more sections, paragraph counts are deliberately uneven rather than mechanically identical. |
| `no_fabricated_experience` | No personal experience, feeling, or result is invented. |

Section headings are editorial phrases derived from the topic, not fixed labels such as "Problem", "Method", or "Conclusion". Paragraph boundaries are intentional. Blog v1 accepts plain paragraph blocks only: do not place Markdown lists, fenced code, or raw HTML in `paragraphs`. Do not repeat the same fact in the lead, body, and closing.

## Source Fidelity

- Preserve verified tool names, file names, commands, errors, decisions, results, and limitations.
- Do not invent a feature, menu, test result, quotation, performance claim, or outcome.
- Make uncertainty explicit when the source does not establish a fact.
- Give every `evidence_point` a unique `evidence_id`, ground it with one or more `source_refs`, and state its `verification` method.
- Make `lead_evidence_refs` and each section's `evidence_refs` resolve to existing evidence IDs.
- Use concrete nouns and observable actions in place of vague benefits such as "efficient", "innovative", or "powerful".
- Keep the reader, user, AI agent, code, and external service distinct whenever their roles matter.

## First-Person Experience

Neutral practitioner prose is the default. First-person markers such as `저는`, `제가`, `직접 해보니`, and `느꼈습니다` are allowed only when the source contains that experience and `first_person_evidence_refs` points exclusively to existing matching `kind: observation` entries with sources and verification. When first-person prose appears, the reference field is required; a missing or nonexistent reference emits `evidence_reference_missing` and may also emit `unsupported_first_person_experience`.

Without that evidence, rewrite the statement as a sourced observation or remove it. A fabricated first-person claim is a validation failure with `unsupported_first_person_experience`.

## Forbidden Canned Prose

Reject formulaic phrases that make unrelated articles sound mechanically identical, including:

- `안녕하세요`
- `오늘은 ~ 알아보겠습니다`
- `결론적으로`
- `도움이 되었기를 바랍니다`
- `지금까지 ~ 알아보았습니다`

Do not replace them with close paraphrases that serve the same empty function. The lead must enter the actual subject, and the closing must resolve the article's central idea. Canned prose produces `canned_prose_forbidden`.

## Title Policy

The title names a concrete problem, choice, result, or useful distinction without promising certainty or speed the evidence cannot support. Reject clickbait expressions including:

- `완벽한`
- `혁신적인`
- `단 몇 분 만에`
- `무조건`
- `100%`
- `한 번에 끝`

A title containing these expressions produces `clickbait_title_forbidden`.

## Visual Editorial Policy

The article requires exactly one `hero_visual` and permits zero to four section visuals. A section visual is justified only when it explains an artifact, workflow, comparison, result, or real use that prose alone would make harder to understand.

For every visual:

- Use `provided_asset` when a source image is available and retain its provenance.
- Use `generated_scene` when a professional explanatory scene is needed; retain the prompt and never present it as `실제 화면`, `실제 캡처`, `실제 스크린샷`, or `actual screenshot`.
- For every `generated_scene`, store the exact internal disclosure `AI 생성 설명 이미지` in both the visual metadata and manifest. Keep that production label out of public `alt_text` and captions.
- Use a PNG or JPEG at least 1200 pixels wide with a ratio of at least `1.5:1`.
- Measure the displayed dimensions after applying EXIF orientation. Reject only a truly blank single-color placeholder; a purposeful flat-color diagram remains acceptable.
- Write meaningful `alt_text` that describes the information conveyed, not "image" or a file name.
- Put one caption immediately below the image. The caption adds a verification point, result, caution, or distinction instead of repeating the paragraph.
- Require a professional editorial composition, legible content, no generation artifacts, and no generic AI motifs.
- Exclude robots, holograms, glowing brains, neon interfaces, floating icons, invented menus, unreadable Korean, and decorative scenes unrelated to the evidence. State these exclusions explicitly in every generated-image prompt.

The blog profile does not inherit the book image rule `len(steps) + 2`. More images do not make an article more credible; evidence-bearing images do.

## Portable Output

The finished article renders to both `blog.md` and `blog.html`.

- Preserve the article's plain paragraph boundaries and topic-specific headings. Escape Markdown and HTML syntax supplied inside content instead of interpreting it.
- The renderer accepts only a JSON object root and reports a concise `adaptive_blog` root error with exit code `1` for a top-level array or other non-object root.
- The renderer writes only beside `blog.json`; a sibling or unrelated output directory is rejected before either output is created.
- Use relative image links, meaningful alt text, and immediate captions in Markdown.
- Use semantic `article`, `header`, `section`, `figure`, and `footer` elements in HTML.
- Add no platform script, tracking code, or platform-specific dependency.
- Do not expose `mode_reason`, `source_refs`, or `humanity_review` in public prose.
- Do not add generic introductory or closing copy during rendering.

The output is designed to avoid canned AI-writing patterns through source fidelity, concrete evidence, varied rhythm, and visible judgment. Never state or imply that it is guaranteed to be indistinguishable from a person or that an AI detector has been defeated.
