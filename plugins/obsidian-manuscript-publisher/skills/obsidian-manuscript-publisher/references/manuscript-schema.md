# Manuscript JSON Contract

`manuscript.json` is publication-ready only when every required field below is present and every Step follows the build contract.

```json
{
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
