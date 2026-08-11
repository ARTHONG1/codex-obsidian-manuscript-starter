# Manuscript JSON Contract

`manuscript.json` is publication-ready only when the selected template contract is explicit and every Step follows that contract. New `book_a4` synthesis MUST use V3. The V1 and V2 contracts below are retained only for historical packages.

## Book A4 V3 Contract

New packages use `template_version: 3` and `editorial_quality_version: 3`. The fixed outer sections remain the chapter title, `[이번 챕터에서는]`, `[한눈에 보기]`, `[미리 보기]`, `[실습하기]`, `[실전 활용하기]`, and `[꿀팁 더하기]`; the number of `practice_blocks` follows the actual build workflow. Each step has sequential numbering, build metadata, a 2-4 sentence body, a completion check, a user/tool interaction, and a topic-specific generated visual. Tips are evidence-driven and may be omitted or repeated as the subject requires; a detailed tip uses 3-5 sentences. `editorial_review` contains the seven weighted quality categories and hard-failure attestations. Every V3 visual brief forbids `red_box`, `numbered_callout`, and `arrow`.

## Legacy Book A4 V1 Contract

```json
{
  "output_profile": "book_a4",
  "source_markdown": "chapter-title.md",
  "part": "Part 1",
  "chapter": "01",
  "title": "chapter title",
  "chapter_intro": "two or three sentences",
  "quick_reference": {"대상": "", "활용 도구": "", "준비물": "", "핵심 기능": ""},
  "preview": {
    "qr_label": "",
    "qr_url": "",
    "result_title": "",
    "result_summary": "",
    "visual": {
      "asset_id": "preview",
      "evidence_kind": "software_result",
      "method": "generated_scene",
      "image": "assets/preview.png",
      "visual_kind": "result_preview",
      "quality_review": {"purpose_match": true, "professional_layout": true, "legible_content": true, "no_generation_artifacts": true, "no_generic_ai_motifs": true, "review_note": "완성 결과가 화면 중심에 명확하게 보입니다."},
      "caption": "그림 1-01-1. 완성된 기술의 구성 화면"
    }
  },
  "steps": [{
    "title": "",
    "body": "two or three build-action sentences",
    "step_kind": "build",
    "build_action": "",
    "artifact": {
      "kind": "file",
      "name": "",
      "paths": ["verified/relative/path"],
      "status": "verified"
    },
    "completion_check": "",
    "interaction": {
      "user_request": "사용자가 Codex에게 기술 제작을 요청한 문장",
      "codex_action": "Codex가 생성·수정·연결·테스트한 결과",
      "user_check": "사용자가 확인하거나 추가 수정 요청한 기준"
    },
    "visual": {
      "asset_id": "step-01",
      "evidence_kind": "workflow",
      "method": "generated_scene",
      "image": "assets/step-01.png",
      "visual_kind": "work_product",
      "quality_review": {"purpose_match": true, "professional_layout": true, "legible_content": true, "no_generation_artifacts": true, "no_generic_ai_motifs": true, "review_note": "이 단계에서 만든 파일과 결과가 분명하게 보입니다."},
      "caption": "그림 1-01-2. 이 단계의 제작 결과 화면"
    }
  }],
  "real_world_use": "two or three sentences",
  "real_world_use_visual": {
    "asset_id": "real-world-use",
    "evidence_kind": "classroom_scene",
    "method": "generated_scene",
    "image": "assets/real-world-use.png",
    "visual_kind": "field_scene",
    "quality_review": {"purpose_match": true, "professional_layout": true, "legible_content": true, "no_generation_artifacts": true, "no_generic_ai_motifs": true, "review_note": "완성된 기술을 실제 업무 맥락에서 보여 줍니다."},
    "caption": "그림 1-01-3. 완성된 기술을 학교 업무에 적용하는 장면"
  },
  "tip": "two or three sentences",
  "verification_note": ""
}
```

## Step Rules

- `steps` is a non-empty ordered list with dynamic length.
- `step_kind` is exactly `build`.
- `build_action`, `artifact.name`, non-empty `artifact.paths`, `artifact.status: verified`, and `completion_check` are required.
- `interaction.user_request`, `interaction.codex_action`, and `interaction.user_check` are required. Render these three sentences in that order so every Step shows the user directing Codex to make a technology, Codex building it, and the user verifying it.
- A use-only Step is invalid even if it has a completed result.
- `title` is a Korean noun phrase that ends in a meaningful work noun such as `준비`, `설계`, `구현`, `검증`, `수정`, `설정`, or `활용`; sentence endings such as `합니다` and `하기` are invalid.
- Interaction prose uses practical present-tense honorifics, not past-tense development-report wording such as `구현했습니다` or `완성했습니다`.

## Visual Rules

- Required visuals are preview, every Step, and real-world use: exactly `len(steps) + 2` slots.
- Every visual uses `method: generated_scene` and a unique `asset_id`.
- Every visual chooses one of `ui_screen`, `work_product`, `workflow_diagram`, `result_preview`, or `field_scene` and records a complete `quality_review`.
- Every caption is `그림 Part-챕터-순번. 설명` in render order. Do not label all generated visuals as examples or reconstructions.
- Every generated visual is at least 1200px wide and landscape: its pixel width divided by height is at least `1.5`; render its single caption directly below the image.
- Every visual references one manifest record with the same method and evidence kind.

## Asset Manifest Rules

Every asset record requires `asset_id`, `output_path`, lowercase 64-character `sha256`, `evidence_kind`, `method: generated_scene`, `prompt`, `visual_kind`, and `quality_review`. `output_path` stays inside the version folder and points to a valid PNG or JPEG.

## Validation and Publication Contract

- `output_profile` is exactly `book_a4`.
- `source_markdown` names one Markdown file in the version root; it cannot contain a directory, backslash, drive prefix, or traversal segment.
- `asset-validation.json` records the exact inputs validated:

```json
{
  "status": "ready",
  "validated_inputs": {
    "manuscript_sha256": "lowercase-64-character-sha256",
    "asset_manifest_sha256": "lowercase-64-character-sha256"
  }
}
```

Publication recalculates both hashes before any REST request. A mismatch is a stale validation failure. The published package contains only the production plan, `source_markdown`, manuscript JSON, asset manifest, asset validation report, rendered HTML/PDF, and the exact manifest-listed assets.

## `book_a4` Desktop Bundle

After fresh validation, successful HTML/PDF rendering, and the independent Vault publication attempt, the selected immutable version may be exported as a `book_a4 desktop bundle`:

```text
00 최신본/
├── 01 본문-복사용.txt
├── 02 원고.md
├── 03 미리보기.html
├── 04 인쇄용.pdf
├── 05 이미지-삽입순서.md
├── images/
└── _meta/export-manifest.json
```

- `01 본문-복사용.txt` is generated from validated structured content and marks each image insertion position explicitly.
- `02 원고.md` and `03 미리보기.html` rewrite only manifest-listed image references to numbered files under `images/`.
- `04 인쇄용.pdf` is copied byte-for-byte from the verified render. It is a layout/print preview, not the primary copy source.
- `05 이미지-삽입순서.md` orders preview, Step 1 through Step N, then real-world use and maps each numbered file to its caption, alt text, asset ID, and hash.
- `_meta/export-manifest.json` contains non-secret hashes and independent Vault publication status. It never contains credentials or private source attachments.

The project directory comes from the registry `destination_root`. `00 최신본` changes only after complete staged hash verification; older immutable versions remain under `99 이전버전/v0.N`.

## Template Version 2

Historical V2 manuscripts set `template_version: 2` while retaining `output_profile: book_a4`. V2 uses `practice_preparation` and ordered `practice_blocks` rather than the legacy top-level `steps` and final `tip` fields:

```json
{
  "template_version": 2,
  "practice_preparation": {"title": "실습 사전 준비", "body": "", "visual": {}},
  "practice_blocks": [
    {"type": "step", "number": 1, "title": "", "body": ["", ""], "interaction": {}, "artifact": {}, "visual": {}},
    {"type": "tip", "after_step": 1, "title": "", "body": ["", ""]},
    {"type": "step", "number": 2, "title": "", "body": ["", "", ""], "interaction": {}, "artifact": {}, "visual": {}}
  ]
}
```

The sequence must alternate Step and tip, begin and end with a Step, and contain exactly N-1 tips for N Steps. Each Step body and each tip body contains two or three non-empty sentences. V2 requires preview, preparation, and Step visuals; a real-world-use visual is optional. Historical packages without `template_version: 2` continue to use the legacy contract above.
