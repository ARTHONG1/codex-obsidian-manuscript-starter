# Book A4 Workflow

Use this reference for new/default `book_a4` synthesis.

Read only named material cards, or active cards in the registered project when none are named. Reconcile duplicates and uncertainty, then run `scripts/select_book_template.py` and `scripts/next_version.py`. New synthesis must use `template_version: 3`, `editorial_quality_version: 3`, flexible `practice_blocks`, and `editorial_review`.

Read `manuscript-schema.md`, `asset-policy.md`, and `master-editorial-profile.md`. Create and verify `production-plan.json`, the version Markdown, `manuscript.json`, and `asset-manifest.json` before requesting visuals. Build Steps must describe real files, code, configuration, tests, or corrections and include an observable completion check.

Preserve the fixed order: chapter title, `[이번 챕터에서는]`, `[한눈에 보기]`, `[미리 보기]`, `[실습하기]` with Step 1 through Step N, `[실전 활용하기]`, `[꿀팁 더하기]`, and the final caution. Step count follows verified build evidence. Use professional wide `generated_scene` visuals with unique IDs, visual briefs, original-size inspection, hashes, captions, privacy status, and no generic AI motifs or instructional overlays.

Run `scripts/validate_manuscript.py`; continue only for `status: ready` with current `validated_inputs`. Then run `scripts/render_manuscript.py`. Publish only the exact allowlist through `scripts/publish_manuscript_version.py`, snapshotting every allowed file before REST, and require byte-for-byte readback. A failed upload remains failed; allocate a fresh immutable version for retry.
