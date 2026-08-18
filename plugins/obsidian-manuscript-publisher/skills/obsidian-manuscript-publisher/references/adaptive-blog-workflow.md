# Adaptive Blog Workflow

Use this reference only when `adaptive_blog` is explicitly selected.

Read `blog-schema.md` and `blog-editorial-policy.md`; do not load the A4 Step structure, book image formula, or PDF renderer into this branch. Use only named material cards or active cards from the exact registered project. Reconcile evidence, choose one source-supported mode (`practical_guide`, `case_story`, or `insight_column`), and resolve every `source_refs` value against stable turn or attachment IDs.

Allocate a fresh lowercase ASCII `02 Blog/<topic-slug>/v0.N`. Write `blog.json` and `asset-manifest.json` with five to seven ordered sections, plain paragraph blocks, evidence IDs, one hero visual, and up to four evidence-bearing section visuals. Generated visuals carry the internal disclosure `AI 생성 설명 이미지`; never call one an actual screenshot.

Run `scripts/validate_blog.py` and continue only for `status: ready`; render with `scripts/render_blog.py` to `blog.md` and `blog.html` only. Publish the exact allowlist through `scripts/publish_manuscript_version.py`, require readback, and report mode, version, evidence count, image count, validation, and publication status. Never claim AI-detector defeat or guaranteed human indistinguishability.
