# Adaptive Blog JSON Contract

Use this contract only for the platform-independent `adaptive_blog` output profile. It is independent of the `book_a4` manuscript schema: a blog package must not reuse the book Step structure, image-count rule, renderer, or Vault destination.

## Version Package

Each immutable blog version is published below `02 Blog/<topic-slug>/v0.N` and contains:

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

Validation must return `status: ready` before rendering or publication. A failed validation must not modify the last verified blog version or any `book_a4` version.

`humanity_review` is a manual editorial attestation completed after a person or Codex has inspected the actual draft against the cited material. The validator checks the field shape, explicit attestations, reference IDs, and other deterministic constraints; it does not independently prove semantic source grounding. Before publication, Codex must separately resolve every `source_refs` value against the active conversation bundle and review whether each cited source really supports the associated claim.

## `blog.json`

Every required text field is non-empty. `sections` contains five to seven ordered sections. Each section has exactly one `role` and must not contain the legacy plural `roles` field; the five required mode roles all appear in canonical order, and one role may repeat only in a contiguous run when the subject needs six or seven sections. Headings and paragraph counts are editorially free within those rules.

```json
{
  "output_profile": "adaptive_blog",
  "mode": "practical_guide",
  "mode_reason": "The source records a repeatable build, an error correction, and a verified result.",
  "title": "A specific, non-clickbait title",
  "slug": "portable-topic-slug",
  "audience": "The readers who can apply this material",
  "dek": "A concise description of the article's value and scope.",
  "lead": "A source-grounded scene, problem, question, contrast, or observed result.",
  "core_idea": "The single idea carried through the article",
  "lead_evidence_refs": [
    "evidence-error"
  ],
  "sections": [
    {
      "heading": "A subject-specific editorial heading",
      "role": "problem",
      "paragraphs": [
        "One or more source-grounded paragraphs."
      ],
      "evidence_refs": [
        "evidence-artifact"
      ],
      "visual": {
        "asset_id": "evidence-result",
        "evidence_kind": "software_result",
        "method": "generated_scene",
        "image": "assets/evidence-result.png",
        "visual_kind": "result_preview",
        "privacy_status": "cleared",
        "disclosure": "AI 생성 설명 이미지",
        "alt_text": "A meaningful description of the evidence shown",
        "caption": "A caption that adds a check, result, or distinction.",
        "quality_review": {
          "purpose_match": true,
          "professional_layout": true,
          "legible_content": true,
          "no_generation_artifacts": true,
          "no_generic_ai_motifs": true,
          "review_note": "The result and its verification point are clear."
        }
      }
    }
  ],
  "evidence_points": [
    {
      "evidence_id": "evidence-artifact",
      "kind": "artifact",
      "detail": "A concrete source-grounded file, command, error, result, comparison, decision, or observation.",
      "source_refs": [
        "conversation-turn-12",
        "files/example.ext"
      ],
      "verification": "How this detail was checked."
    },
    {
      "evidence_id": "evidence-error",
      "kind": "result",
      "detail": "A second concrete and independently traceable detail.",
      "source_refs": [
        "conversation-turn-18"
      ],
      "verification": "How the result was checked."
    }
  ],
  "next_action": "A specific action the reader can take next.",
  "closing": "A closing that returns to the central idea without generic filler.",
  "tags": [
    "topic",
    "audience"
  ],
  "meta_description": "A portable description for publishing platforms.",
  "hero_visual": {
    "asset_id": "hero",
    "evidence_kind": "software_result",
    "method": "provided_asset",
    "image": "assets/hero.png",
    "visual_kind": "result_preview",
    "privacy_status": "cleared",
    "alt_text": "A meaningful description of the article's verified subject",
    "caption": "A caption that identifies the result or interpretation shown.",
    "quality_review": {
      "purpose_match": true,
      "professional_layout": true,
      "legible_content": true,
      "no_generation_artifacts": true,
      "no_generic_ai_motifs": true,
      "review_note": "The article subject and evidence are immediately clear."
    }
  },
  "humanity_review": {
    "source_grounded_opening": true,
    "central_idea_consistency": true,
    "concrete_evidence": true,
    "visible_judgment": true,
    "varied_rhythm": true,
    "no_fabricated_experience": true,
    "review_note": "The article uses traced evidence and records why key choices were made."
  }
}
```

## Editorial Modes and Roles

`mode` is exactly one of the following values. Its sections collectively include every required role for that mode; additional headings remain topic-specific rather than fixed template labels.

| `mode` | Required section roles |
|---|---|
| `practical_guide` | `problem`, `principle`, `method`, `evidence`, `application` |
| `case_story` | `before`, `turning_point`, `process`, `result`, `lesson` |
| `insight_column` | `observation`, `contrast`, `principle`, `example`, `implication` |

The role sequence is canonical. Six- or seven-section articles may split a substantial role into adjacent sections, such as `problem`, `problem`, `principle`, `method`, `evidence`, `evidence`, `application`. A role may not reappear after the sequence has advanced, and `supporting` or any unknown role is invalid.

`mode_reason` records the source evidence that justified the selected mode. It is internal production metadata and is not rendered into public prose.

## Evidence Contract

`evidence_points` contains at least two entries. Each entry requires a unique non-empty `evidence_id`, `kind`, `detail`, one or more `source_refs`, and `verification`. `lead_evidence_refs` and every section's `evidence_refs` are non-empty lists whose values resolve to existing evidence IDs.

Accepted `kind` values are:

- `artifact`
- `error`
- `result`
- `comparison`
- `decision`
- `observation`

First-person experience in public prose is supported only when `first_person_evidence_refs` points exclusively to existing `observation` evidence with non-empty sources and verification. When first-person prose appears, this field is required and every reference must resolve; a missing or nonexistent reference emits `evidence_reference_missing` and may also emit `unsupported_first_person_experience`. The preferred default is neutral practitioner prose; omit the field only when the article contains no first-person experience. When sourced first-person experience is necessary, use this optional field:

```json
"first_person_evidence_refs": ["evidence-observation"]
```

## Paragraph Block Contract

Blog v1 supports plain paragraph blocks only. Every `paragraphs` value is a non-empty list of plain strings. Do not place raw Markdown lists, ordered-list markers, fenced code blocks, or raw HTML in these strings. A later schema version may add typed list or code blocks without changing the meaning of v1.

## Visual Contract

- `hero_visual` is required exactly once.
- A section may have one optional `visual`; the complete article has zero to four section visuals.
- Every visual requires a unique `asset_id`, `evidence_kind`, `method`, version-local `image`, `visual_kind`, `privacy_status`, non-empty `alt_text`, `caption`, and complete `quality_review`.
- Supported methods are exactly `provided_asset` and `generated_scene`.
- Every image is PNG or JPEG, at least 1200 pixels wide, and landscape with a width-to-height ratio of at least `1.5`.
- Apply EXIF orientation before measuring image width and aspect ratio. Reject a truly blank single-color placeholder, but do not reject a meaningful flat-color diagram merely because it uses a small palette.
- A generated visual must carry the exact internal metadata `"disclosure": "AI 생성 설명 이미지"` in both `blog.json` and `asset-manifest.json`. That internal label must not appear in public `alt_text` or `caption`, and public text must not claim `실제 화면`, `실제 캡처`, `실제 스크린샷`, or `actual screenshot`. A provided asset retains source provenance in its manifest record.
- Generated-image prompts explicitly prohibit floating icons, invented menus, and unreadable Korean in addition to robots, holograms, glowing brains, and neon interfaces. Alternative text must describe conveyed information; generic labels such as `image`, `사진`, or an image filename are invalid.
- The blog profile does not inherit the book formula `len(steps) + 2`.

Every `quality_review` contains the five true checks `purpose_match`, `professional_layout`, `legible_content`, `no_generation_artifacts`, and `no_generic_ai_motifs`, plus a concrete `review_note`.

## `asset-manifest.json`

```json
{
  "assets": [
    {
      "asset_id": "hero",
      "output_path": "assets/hero.png",
      "sha256": "lowercase-64-character-sha256",
      "evidence_kind": "software_result",
      "method": "provided_asset",
      "visual_kind": "result_preview",
      "privacy_status": "cleared",
      "alt_text": "Meaningful alternative text",
      "quality_review": {
        "purpose_match": true,
        "professional_layout": true,
        "legible_content": true,
        "no_generation_artifacts": true,
        "no_generic_ai_motifs": true,
        "review_note": "The visual is suitable for publication."
      },
      "source": {
        "kind": "conversation_attachment",
        "reference": "conversation-turn-18"
      }
    },
    {
      "asset_id": "evidence-result",
      "output_path": "assets/evidence-result.png",
      "sha256": "lowercase-64-character-sha256",
      "evidence_kind": "software_result",
      "method": "generated_scene",
      "visual_kind": "result_preview",
      "privacy_status": "cleared",
      "alt_text": "Meaningful alternative text",
      "quality_review": {
        "purpose_match": true,
        "professional_layout": true,
        "legible_content": true,
        "no_generation_artifacts": true,
        "no_generic_ai_motifs": true,
        "review_note": "The visual is suitable for publication."
      },
      "prompt": "wide landscape composition, 16:9, professional editorial layout, no robot, no hologram, no neon interface",
      "disclosure": "AI 생성 설명 이미지"
    }
  ]
}
```

Every manifest `output_path` stays inside the version directory, resolves to the corresponding visual file, and matches the file's lowercase SHA-256 digest. Asset IDs are unique across hero and section visuals.

## Rendering Contract

The renderer accepts only a ready package whose `output_profile` is `adaptive_blog`. The supplied output directory must be exactly the directory containing `blog.json`; it writes `blog.md` and `blog.html` there as one atomic pair.

- Markdown uses portable headings, preserved paragraph blocks, relative image links, alt text, and immediate captions. The renderer escapes Markdown syntax from content strings instead of interpreting it.
- HTML uses semantic `article`, `header`, `section`, `figure`, and `footer` elements with restrained embedded preview CSS.
- HTML contains no platform script or tracking code.
- Public output omits internal fields including `mode_reason`, `source_refs`, and `humanity_review`.
- A profile mismatch produces no partial Markdown or HTML output.

## Deterministic Validation Errors

The validator uses these error codes for the tested contract failures:

| Code | Condition |
|---|---|
| `blog_profile_required` | `output_profile` is not exactly `adaptive_blog`. |
| `blog_section_count_invalid` | The article has fewer than five or more than seven sections. |
| `section_role_required` | A section does not contain exactly one singular `role` field. |
| `section_roles_forbidden` | A section contains the legacy plural `roles` field, even when `role` is also valid. |
| `section_role_invalid` | A section uses a role outside the selected mode. |
| `mode_roles_incomplete` | The selected mode is missing one or more required semantic roles. |
| `mode_roles_out_of_order` | Required roles are not in canonical order or a repeated role is not contiguous. |
| `insufficient_evidence` | Fewer than two evidence points are present. |
| `duplicate_evidence_id` | Two evidence points use the same `evidence_id`. |
| `lead_evidence_refs_required` | The lead has no evidence reference. |
| `section_evidence_refs_required` | A section has no evidence reference. |
| `evidence_reference_missing` | A lead, section, or first-person reference does not resolve to an evidence point. |
| `paragraph_block_format_invalid` | A paragraph contains a raw Markdown list, fenced code block, or raw HTML tag. |
| `canned_prose_forbidden` | Public prose contains a forbidden canned phrase. |
| `clickbait_title_forbidden` | The title contains a forbidden clickbait expression. |
| `unsupported_first_person_experience` | First-person experience lacks a source-referenced `observation` evidence point. |
| `uniform_section_rhythm` | Three or more sections all use the same paragraph count. |
| `visual_alt_text_required` | A visual has empty or missing `alt_text`. |
| `visual_alt_text_uninformative` | A visual uses generic or filename-only alternative text. |
| `asset_alt_text_uninformative` | A manifest asset uses generic or filename-only alternative text. |
| `duplicate_asset_id` | A manifest repeats an `asset_id`. |
| `asset_path_not_version_local` | An asset path escapes the immutable version directory. |
| `asset_hash_mismatch` | The recorded SHA-256 does not match the asset bytes. |
| `landscape_image_required` | An image has a width-to-height ratio below `1.5`. |
| `visual_minimum_resolution_required` | An image is less than 1200 pixels wide. |
| `generated_visual_disclosure_required` | Generated visual metadata or its manifest omits the exact internal disclosure. |
| `generated_visual_public_disclosure_forbidden` | Public generated-visual alt text or caption exposes `AI 생성 설명 이미지`. |
| `generated_visual_actual_screenshot_claim` | Public generated-visual alt text or caption claims `실제 화면`, `실제 캡처`, `실제 스크린샷`, or `actual screenshot`. |

## `adaptive_blog` Desktop Bundle

After fresh validation, successful Markdown/HTML rendering, and the independent Vault publication attempt, the selected immutable version may be exported as an `adaptive_blog desktop bundle`:

```text
00 최신본/
├── 01 본문-복사용.txt
├── 02 블로그.md
├── 03 미리보기.html
├── 04 이미지-삽입순서.md
├── images/
└── _meta/export-manifest.json
```

- `01 본문-복사용.txt` follows the validated article order and inserts an explicit marker and caption where each visual belongs.
- `02 블로그.md` and `03 미리보기.html` rewrite only manifest-listed image references to numbered files under `images/`.
- `04 이미지-삽입순서.md` orders the hero visual first and section visuals in article order, with caption, alt text, asset ID, source filename, and hash.
- `_meta/export-manifest.json` contains non-secret traceability and the Vault publication outcome independently from desktop export.

The `adaptive_blog desktop bundle never contains a PDF`. Export must not create one, copy one from a neighboring folder, or inherit the `book_a4` PDF rule. The project directory comes from registry `destination_root`, `00 최신본` changes only after staged hash verification, and older immutable versions remain under `99 이전버전/v0.N`.
