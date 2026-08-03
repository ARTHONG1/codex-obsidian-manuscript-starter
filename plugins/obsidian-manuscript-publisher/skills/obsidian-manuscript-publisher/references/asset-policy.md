# Required Generated Asset Policy

Every manuscript version keeps a self-contained visual snapshot under `v0.N/assets`. New manuscript visuals use Codex built-in image generation and `generated_scene only`; no user or external image API key is required.

## Required Slots

- Preview: one generated image.
- Steps: one generated image for every Step 1 through Step N.
- Real-world use: one generated image.
- Total: `len(steps) + 2`.

## Relevance and Visual Kind

Generate after Step meanings are final. Each image must visualize the artifact or build change in its slot. Select exactly one `visual_kind` before writing its generation prompt:

- `ui_screen`: a realistic, tidy software setting or execution screen.
- `work_product`: a working file, code, document, or project structure screen.
- `workflow_diagram`: a restrained editorial diagram of the automation flow.
- `result_preview`: the completed CSV, document, web page, or message result.
- `field_scene`: a realistic school-work or classroom application scene.

Generic decorative scenes do not satisfy any kind. Do not use robots, holograms, glowing brains, neon interfaces, floating icons, generic laptop poses, invented menus, unreadable Korean, or unrelated charts. UI visuals use only short, verified labels; they do not attempt to generate long Korean paragraphs inside the image.

Generate every visual as a wide landscape composition. Put `wide landscape composition, 16:9`, `professional`, `editorial`, and an explicit prohibition of robot, hologram, and neon-interface motifs in every prompt. Require an actual width of at least 1200px and a width-to-height ratio of at least `1.5`.

After generation, inspect the selected source at original size with `view_image`. Confirm the image matches its purpose, has a professional layout, has legible content, has no generation artifacts, and has no generic AI motifs. Revise the prompt once when any check fails. A second failure stops publication.

## Version-Local Record

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
- a numbered editorial caption in render order: `그림 Part-챕터-순번. 설명`

The validator checks file existence, PNG/JPEG signature, non-zero content, width, landscape ratio, version-local path, hash, prompt, visual kind, quality review, numbered caption, method, and unique slot assignment.

At publication, only manifest-listed assets under the version-local `assets/` directory are allowed. An unlisted image, duplicate path, duplicate asset ID, path traversal, or a manifest/visual path mismatch stops publication before any Local REST request.

## Failure

Revise a failed generation prompt once. A second failure returns `image_generation_failed` and stops Markdown finalization, HTML/PDF rendering, and Vault publication. Never emit a blank panel or partially illustrated manuscript.
