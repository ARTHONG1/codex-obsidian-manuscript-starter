# Manuscript Editorial Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the existing Obsidian manuscript format and workflow while enforcing nominal Korean Step titles, practical present-tense prose, and professional purpose-specific AI visuals.

**Architecture:** Extend the existing manuscript JSON contract with `visual_kind` and auditable `quality_review` metadata. Enforce the new editorial rules in `validate_manuscript.py`, keep rendering presentation-only, and make the skill and references tell Codex how to generate and visually review each asset before publication.

**Tech Stack:** Python 3.12, Pillow, ReportLab, HTML/CSS, JSON, unittest, Codex `imagegen` and `view_image`, Obsidian Local REST API.

## Global Constraints

- Preserve the fixed section order and four-row quick-reference table.
- Preserve dynamic Step 1 through Step N; never force five Steps.
- Preserve one 2–3 sentence paragraph for each Step.
- Preserve A4 portrait HTML/PDF, version immutability, REST publication, deletion, and binary hash verification.
- Use Codex built-in image generation only; do not add an external image API.
- Do not modify or republish earlier manuscript versions.
- Require one preview visual, one visual per Step, and one real-world-use visual.

---

### Task 1: Encode the nominal Step-title contract with failing tests

**Files:**
- Modify: `tests/test_manuscript_renderer.py:21-175`
- Modify: `tests/test_obsidian_manuscript_workspace.py:23-33`

**Interfaces:**
- Consumes: the current `write_valid_package()` fixture and validator CLI.
- Produces: regression tests for `validate_step_title(title: str, index: int) -> list[dict]` and the new skill wording.

- [ ] **Step 1: Change the valid fixture to a noun-phrase title**

Use `"title": "자동화 Skill 구조와 실행 스크립트 구현"` instead of the current sentence-style title.

- [ ] **Step 2: Add a failing test for sentence-style titles**

```python
def test_validator_rejects_sentence_style_step_titles(self):
    with tempfile.TemporaryDirectory() as temporary:
        manuscript, manifest, report = self.write_valid_package(Path(temporary))
        payload = json.loads(manuscript.read_text(encoding="utf-8"))
        payload["steps"][0]["title"] = "Codex에게 제작 목표를 전달합니다"
        manuscript.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        result, validation = self.validate_package(manuscript, manifest, report)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("step_title_sentence_style_forbidden", {issue["code"] for issue in validation["errors"]})
```

- [ ] **Step 3: Add a failing test for `-하기` titles**

Use `"뉴스 브리핑 규칙 설계하기"` and expect `step_title_nominal_required`.

- [ ] **Step 4: Add an acceptance test for representative nominal endings**

Test `준비`, `설계`, `구현`, `연결`, `설정`, `검증`, `수정`, `설치`, `배포`, and `활용` as valid final tokens.

- [ ] **Step 5: Run the tests and confirm the new cases fail for the expected missing behavior**

Run:

```powershell
# Set CODEX_BUNDLED_PYTHON to the bundled Python executable for the active Codex installation.
& $env:CODEX_BUNDLED_PYTHON -m unittest tests.test_manuscript_renderer -v
```

Expected: the new title tests fail while existing tests still run.

- [ ] **Step 6: Commit the test contract**

```powershell
git add tests/test_manuscript_renderer.py tests/test_obsidian_manuscript_workspace.py
git commit -m "test: define manuscript editorial title contract"
```

---

### Task 2: Implement Step-title and practical-prose validation

**Files:**
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/validate_manuscript.py:28-88`
- Test: `tests/test_manuscript_renderer.py`

**Interfaces:**
- Consumes: `step["title"]` and the three `interaction` strings.
- Produces: `validate_step_title()` and `validate_practical_prose()` issue lists consumed by `validate_step()`.

- [ ] **Step 1: Add explicit title constants**

```python
NOMINAL_STEP_ENDINGS = {
    "준비", "분석", "설계", "구성", "구현", "연결", "설정", "생성",
    "비교", "검증", "수정", "테스트", "설치", "배포", "실행", "적용",
    "활용", "정리",
}
SENTENCE_STYLE_ENDINGS = ("하기", "합니다", "하세요", "해보기", "해 봅니다", ".")
REPORT_TENSE_PATTERNS = ("구현했습니다", "완성했습니다", "추가했습니다", "요청했습니다", "되었습니다")
```

- [ ] **Step 2: Implement the title validator**

```python
def validate_step_title(title: str, index: int) -> list[dict]:
    value = str(title or "").strip()
    if not value:
        return [_issue("step_title_nominal_required", step=index)]
    if value.endswith(SENTENCE_STYLE_ENDINGS):
        return [_issue("step_title_sentence_style_forbidden", step=index)]
    if value.split()[-1] not in NOMINAL_STEP_ENDINGS:
        return [_issue("step_title_nominal_required", step=index)]
    return []
```

- [ ] **Step 3: Implement obvious report-style rejection without pretending to judge all Korean prose**

Inspect `interaction.user_request`, `codex_action`, and `user_check`; reject only the explicit past-report patterns above. Preserve natural current-tense endings such as `요청합니다`, `생성합니다`, and `확인합니다`.

- [ ] **Step 4: Call both validators from `validate_step()`**

Append their issues before artifact and interaction validation so failures identify the exact Step.

- [ ] **Step 5: Run targeted and full tests**

Run the Task 1 command, then:

```powershell
& $env:CODEX_BUNDLED_PYTHON -m unittest tests.test_manuscript_renderer tests.test_obsidian_manuscript_workspace -v
```

Expected: all title and prose tests pass with no regression.

- [ ] **Step 6: Commit**

```powershell
git add plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/validate_manuscript.py tests/test_manuscript_renderer.py
git commit -m "feat: enforce nominal manuscript step titles"
```

---

### Task 3: Define purpose-specific professional visual metadata

**Files:**
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/manuscript-schema.md:5-81`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/asset-policy.md:1-35`
- Modify: `tests/test_manuscript_renderer.py:21-80`

**Interfaces:**
- Consumes: each visual and matching asset-manifest record.
- Produces: `visual_kind` and `quality_review` fields for Task 4 validation.

- [ ] **Step 1: Extend each test visual and manifest record**

```json
{
  "visual_kind": "ui_screen",
  "quality_review": {
    "purpose_match": true,
    "professional_layout": true,
    "legible_content": true,
    "no_generation_artifacts": true,
    "no_generic_ai_motifs": true,
    "review_note": "작업 화면의 구조와 결과 파일이 명확하게 보임"
  }
}
```

- [ ] **Step 2: Prepare numbered captions that remain compatible with the current validator**

Generate captions in render order:

```text
그림 1-01-1. 완성된 자동화 Skill의 구성 예시 화면
그림 1-01-2. Skill 파일과 실행 스크립트 구현 예시 화면
그림 1-01-3. 완성된 Skill을 학교 업무에 적용하는 예시 이미지
```

- [ ] **Step 3: Document the five allowed visual kinds**

Define `ui_screen`, `work_product`, `workflow_diagram`, `result_preview`, and `field_scene` with purpose, required composition, and prohibited motifs.

- [ ] **Step 4: Document the mandatory visual review sequence**

Require image generation, original-size `view_image` inspection, five quality decisions, one prompt-based retry, and publication stop after a second failure.

- [ ] **Step 5: Run the existing suite after the schema and fixture update**

The current validator may ignore the new metadata, but all existing tests must remain green because this task only establishes the documented data shape.

- [ ] **Step 6: Commit the documented contract and compatible fixture**

```powershell
git add plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references tests/test_manuscript_renderer.py
git commit -m "test: define professional manuscript visual contract"
```

---

### Task 4: Enforce image purpose, quality records, resolution, prompts, and captions

**Files:**
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/validate_manuscript.py:15-31`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/validate_manuscript.py:90-214`
- Test: `tests/test_manuscript_renderer.py`

**Interfaces:**
- Consumes: version-local image files, visual metadata, manifest prompt, Part, chapter, and render order.
- Produces: deterministic visual validation issues and `status: ready` only for complete packages.

- [ ] **Step 1: Add failing tests for missing visual kind, missing quality review, low resolution, weak prompts, and unnumbered captions**

Expected error codes: `visual_kind_required`, `visual_quality_review_required`, `visual_minimum_resolution_required`, `unprofessional_prompt_contract`, and `figure_caption_format_required`. Run only the new cases first and confirm each fails for the missing validator behavior.

- [ ] **Step 2: Add visual constants**

```python
VISUAL_KINDS = {"ui_screen", "work_product", "workflow_diagram", "result_preview", "field_scene"}
QUALITY_FLAGS = (
    "purpose_match", "professional_layout", "legible_content",
    "no_generation_artifacts", "no_generic_ai_motifs",
)
MIN_IMAGE_WIDTH = 1200
PROHIBITED_AI_MOTIFS = ("robot", "hologram", "glowing brain", "neon interface")
```

- [ ] **Step 3: Implement metadata validation**

Require an allowed `visual_kind`, all five quality flags equal to `true`, and a non-empty `review_note`. Do not treat the booleans as visual proof; the skill workflow must create them only after `view_image` inspection.

- [ ] **Step 4: Extend binary image validation**

After Pillow opens the image, require `width >= 1200` in addition to the existing ratio and signature checks.

- [ ] **Step 5: Validate prompt specificity**

Require the prompt to mention the selected visual kind’s subject, `wide landscape composition, 16:9`, professional editorial or realistic software presentation, and explicit exclusion of generic AI motifs. Reject prompts that positively request any prohibited motif.

- [ ] **Step 6: Validate numbered captions in render order**

Add:

```python
def expected_caption_prefix(part: str, chapter: str, sequence: int) -> str:
    part_number = re.search(r"\d+", part).group(0)
    return f"그림 {part_number}-{chapter}-{sequence}. "
```

Apply sequence 1 to preview, 2 through N+1 to Steps, and N+2 to real-world use. Require a descriptive phrase after the prefix and reject `예시 이미지:` editor notes.

- [ ] **Step 7: Run all manuscript tests**

Expected: new quality tests and all previous binary, landscape, interaction, rendering, and version tests pass.

- [ ] **Step 8: Commit**

```powershell
git add plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/validate_manuscript.py tests/test_manuscript_renderer.py
git commit -m "feat: validate professional manuscript visuals"
```

---

### Task 5: Update the publisher skill’s writing and image-generation workflow

**Files:**
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/SKILL.md:61-140`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/SKILL.md:164-173`
- Test: `tests/test_obsidian_manuscript_workspace.py`

**Interfaces:**
- Consumes: approved editorial and image contracts from Tasks 2–4.
- Produces: generation instructions Codex follows before writing `manuscript.json` and `asset-manifest.json`.

- [ ] **Step 1: Add a nominal-title rule immediately after dynamic Step selection**

State that the title summarizes the meaningful work unit and ends in a concrete noun such as 준비, 설계, 구현, 검증, 수정, 설정, 설치, or 활용. Include accepted and rejected Korean examples.

- [ ] **Step 2: Replace report-style interaction guidance**

Require present-tense instructional prose in the order `준비·결정 → Codex 요청·작업 → 결과 확인·수정 요청`, while retaining one paragraph of 2–3 sentences.

- [ ] **Step 3: Replace the single generic image recipe with visual-kind selection**

Before generating each image, choose one of the five kinds based on the Step’s artifact and completion check. Include the approved anti-AI-art prohibitions and the short-text rule for UI images.

- [ ] **Step 4: Require visual inspection before manifest finalization**

The skill must call `view_image` at original detail, record the five quality flags only after inspection, revise the prompt once on failure, and stop publication after a second failure.

- [ ] **Step 5: Replace mandatory `예시 이미지` captions with numbered editorial captions**

Require truthful, neutral wording. Forbid calling a generated image an actual screenshot, but do not force every caption to say `재현 화면`.

- [ ] **Step 6: Expand skill contract tests**

Assert the skill contains `noun phrase`, all five `visual_kind` values, `view_image`, the five quality checks, and the ban on generic robots/holograms.

- [ ] **Step 7: Run skill and manuscript tests, then commit**

```powershell
& $env:CODEX_BUNDLED_PYTHON -m unittest tests.test_obsidian_manuscript_workspace tests.test_manuscript_renderer -v
git add plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/SKILL.md tests/test_obsidian_manuscript_workspace.py
git commit -m "docs: refine manuscript writing and image workflow"
```

---

### Task 6: Update renderer caption checks without changing the A4 layout

**Files:**
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/render_manuscript.py:28-103`
- Modify: `tests/test_manuscript_renderer.py:105-156`

**Interfaces:**
- Consumes: validator-approved numbered captions and professional landscape images.
- Produces: unchanged A4 HTML/PDF layout with the numbered caption immediately below each image.

- [ ] **Step 1: Write a failing direct-render test for a numbered caption**

Confirm the renderer accepts `그림 1-01-2. Skill 구현 화면` without `예시 이미지` and still keeps `<figcaption>` inside the same `<figure>`.

- [ ] **Step 2: Remove `EXAMPLE_LABELS` from renderer-only validation**

`required_image_path()` should require a non-empty caption and valid image, leaving numbering and semantics to `validate_manuscript.py`.

- [ ] **Step 3: Preserve layout behavior**

Do not change A4 size, margins, `KeepTogether`, image width, image order, or caption position.

- [ ] **Step 4: Render HTML and PDF from the valid fixture**

Verify numbered captions appear under preview, Step, and real-world-use images and no `예시 이미지:` editor label remains.

- [ ] **Step 5: Run the full renderer suite and commit**

```powershell
& $env:CODEX_BUNDLED_PYTHON -m unittest tests.test_manuscript_renderer -v
git add plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/render_manuscript.py tests/test_manuscript_renderer.py
git commit -m "feat: render numbered editorial image captions"
```

---

### Task 7: Perform end-to-end regression and publication-package checks

**Files:**
- Modify if required by verified failures only: files changed in Tasks 1–6
- Verify: `README.md`, plugin bootstrap copies, plugin manifest, and all tests

**Interfaces:**
- Consumes: completed editorial contract implementation.
- Produces: release evidence that manuscript-only refinements did not break installation or Obsidian publication.

- [ ] **Step 1: Run PowerShell installer and privacy contracts**

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
Invoke-Pester -Script '.\tests\InstallerContract.Tests.ps1','.\tests\SecretScan.Tests.ps1'
```

Expected: all tests pass and no credential, certificate, author path, or bytecode is tracked.

- [ ] **Step 2: Run all Python manuscript tests**

```powershell
& $env:CODEX_BUNDLED_PYTHON -m unittest tests.test_manuscript_renderer tests.test_obsidian_manuscript_workspace -v
```

Expected: all tests pass.

- [ ] **Step 3: Validate the plugin and both skills**

Use an isolated `PyYAML==6.0.2` directory and `PYTHONUTF8=1`, then run the official plugin validator and quick validator for both skills.

- [ ] **Step 4: Render a representative multi-Step fixture**

Use at least four nominal Step titles covering preparation, design, implementation, and verification. Render A4 HTML/PDF, rasterize every page, and inspect title wrapping, paragraph density, image professionalism, immediate captions, page breaks, and the final tip box.

- [ ] **Step 5: Verify scope isolation**

Confirm with `git diff --stat` that conversation archiving, deletion, REST upload, installer, and version allocation files are unchanged unless a regression test proved a required compatibility fix.

- [ ] **Step 6: Commit the verified release state**

```powershell
git add plugins/obsidian-manuscript-publisher tests docs/superpowers
git commit -m "feat: improve manuscript editorial quality"
```

- [ ] **Step 7: Stop before GitHub push**

Report the local branch, commits, and verification results. Push to `ARTHONG1/codex-obsidian-manuscript-starter` only after the user explicitly approves publication of this update.
