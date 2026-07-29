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
      "caption": "예시 화면: 완성된 기술의 구성을 확인합니다."
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
      "caption": "예시 이미지: 이 단계의 제작 결과를 확인합니다."
    }
  }],
  "real_world_use": "two or three sentences",
  "real_world_use_visual": {
    "asset_id": "real-world-use",
    "evidence_kind": "classroom_scene",
    "method": "generated_scene",
    "image": "assets/real-world-use.png",
    "caption": "예시 이미지: 완성된 기술을 학교 업무에 적용하는 장면입니다."
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

## Visual Rules

- Required visuals are preview, every Step, and real-world use: exactly `len(steps) + 2` slots.
- Every visual uses `method: generated_scene` and a unique `asset_id`.
- Every generated caption contains `예시 이미지` or `예시 화면`.
- Every generated visual is landscape: its pixel width divided by height is at least `1.5`; render its single caption directly below the image.
- Every visual references one manifest record with the same method and evidence kind.

## Asset Manifest Rules

Every asset record requires `asset_id`, `output_path`, lowercase 64-character `sha256`, `evidence_kind`, `method: generated_scene`, and `prompt`. `output_path` stays inside the version folder and points to a valid PNG or JPEG.
