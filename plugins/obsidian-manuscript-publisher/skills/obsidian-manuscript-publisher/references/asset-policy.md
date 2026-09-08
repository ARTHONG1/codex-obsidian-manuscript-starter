# Required Generated Asset Policy

Keep each publication's visuals in its version-local assets. The selected profile defines allowed visual methods, slots, dimensions, and caption format. Blog source images may use `provided_asset` as specified in `blog-editorial-policy.md`; generated visuals use Codex built-in image generation and `generated_scene`. Custom layout requirements come from the approved template. No external image API key is required.

## Required Slots

- For `adaptive_blog`, use the hero and optional section visuals defined in `blog-schema.md`.
- For `custom_manuscript`, use the approved template's image components and layout contract.
- Do not add a fixed preview/Step/real-world-use image count independently of the selected profile.

## Relevance and Visual Kind

Generate after the section or block meaning is final. Each image must visualize the artifact or build change in its slot. Select exactly one `visual_kind` before writing its generation prompt:

- `ui_screen`: a realistic, tidy software setting or execution screen.
- `work_product`: a working file, code, document, or project structure screen.
- `workflow_diagram`: a restrained editorial diagram of the automation flow.
- `result_preview`: the completed CSV, document, web page, or message result.
- `field_scene`: a realistic school-work or classroom application scene.

Generic decorative scenes do not satisfy any kind. Do not use robots, holograms, glowing brains, neon interfaces, floating icons, generic laptop poses, invented menus, unreadable Korean, or unrelated charts. UI visuals use only short, verified labels; they do not attempt to generate long Korean paragraphs inside the image.

For landscape slots, put `wide landscape composition, 16:9`, `professional`, `editorial`, and an explicit prohibition of robot, hologram, and neon-interface motifs in the prompt. The blog requires actual width of at least 1200px and a width-to-height ratio of at least `1.5`; custom dimensions follow the approved layout.

After generation, inspect the selected source at original size with `view_image`. Confirm the image matches its purpose, has a professional layout, has legible content, has no generation artifacts, and has no generic AI motifs. Revise the prompt once when any check fails. A second failure stops publication.

## Version-Local Record

The manifest schema and automatic checks below describe `adaptive_blog`. For `custom_manuscript`, follow `custom-manuscript-workflow.md`: use input `assets` records and `editorial_review`, preserved with safe output bindings in `custom-validation.json`. Do not add a blog `asset-manifest.json` to a custom package. Shared visual review requirements above still apply; a hash validator is not a semantic image-quality judge.

Each selected asset is copied into `v0.N/assets` and recorded in `asset-manifest.json` with:

- unique `asset_id`
- manuscript slot and evidence kind
- `method: generated_scene`
- generation prompt
- version-local `output_path`
- lowercase SHA-256
- privacy status
- `visual_kind`
- `quality_review` with five true flags and a concise review note
- a caption immediately below the image, using the selected profile's caption format

The validator checks file existence, PNG/JPEG signature, non-zero content, width, landscape ratio, version-local path, hash, prompt, visual kind, quality review, numbered caption, method, and unique slot assignment.

At publication, only manifest-listed assets under the version-local `assets/` directory are allowed. An unlisted image, duplicate path, duplicate asset ID, path traversal, or a manifest/visual path mismatch stops publication before any Local REST request.

## Failure

Revise a failed generation prompt once. A second failure returns `image_generation_failed` and stops Markdown finalization, HTML/PDF rendering, and Vault publication. Never emit a blank panel or partially illustrated manuscript.

## Clean Editorial Visuals

Codex visuals are clean generated scenes: no automatic red boxes, numbered callouts, arrows, borders, or other instructional overlays are added. Long Korean prose must not be delegated to the image model. Preserve the prompt, visual kind, dimensions, hash, privacy state, and quality review in the version-local manifest. Existing historical outputs are preserved without regeneration.
