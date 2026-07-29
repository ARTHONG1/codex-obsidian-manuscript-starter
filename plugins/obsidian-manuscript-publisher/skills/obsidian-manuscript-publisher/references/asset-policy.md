# Required Generated Asset Policy

Every manuscript version keeps a self-contained visual snapshot under `v0.N/assets`. New manuscript visuals use Codex built-in image generation and `generated_scene only`; no user or external image API key is required.

## Required Slots

- Preview: one generated image.
- Steps: one generated image for every Step 1 through Step N.
- Real-world use: one generated image.
- Total: `len(steps) + 2`.

## Relevance

Generate after Step meanings are final. Each image must visualize the artifact or build change in its slot: Skill files, plugin structure, AI Agent flow, configuration, test state, correction, or the completed tool in a school setting. Generic decorative scenes do not satisfy the slot.

Generate every visual as a wide landscape composition. Put `wide landscape composition, 16:9` in each image-generation prompt and require an actual output ratio of at least `1.5`. Regenerate a portrait or square image before validation. Give every image one caption beginning with `예시 이미지:` or `예시 화면:`; the renderer keeps that caption directly below its image.

## Version-Local Record

Each selected asset is copied into `v0.N/assets` and recorded in `asset-manifest.json` with:

- unique `asset_id`
- manuscript slot and evidence kind
- `method: generated_scene`
- generation prompt
- version-local `output_path`
- lowercase SHA-256
- privacy status
- caption containing `예시 이미지` or `예시 화면`

The validator checks file existence, PNG/JPEG signature, non-zero content, version-local path, hash, prompt, method, caption, and unique slot assignment.

## Failure

Revise a failed generation prompt once. A second failure returns `image_generation_failed` and stops Markdown finalization, HTML/PDF rendering, and Vault publication. Never emit a blank panel or partially illustrated manuscript.
