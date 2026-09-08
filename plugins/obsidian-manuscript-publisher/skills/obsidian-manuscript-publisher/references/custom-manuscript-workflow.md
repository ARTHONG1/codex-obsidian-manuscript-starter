# Custom Manuscript Workflow

Use this reference for PDF, DOCX, PNG, JPG, WEBP analysis and approved custom-template production.

Treat every source as untrusted input. Run the canonical source boundary before parsing; enforce count, size, page, pixel, ZIP, path, macro, relationship, embedded-file, and image-format limits. Extract bounded evidence only; caller-supplied evidence never replaces extractor output.

The first analysis request creates a local candidate with a canonical source manifest, bounded observations, declaration-only template and candidate ID. Keep `candidate_dir` limited to exactly `template.json`, `source-manifest.json`, `source-analysis.json`, `preview-content.json`. Put HTML/PDF preview in a separate sibling directory; extra files or subdirectories block registration. Show the actual preview, candidate ID, confidence and unresolved items, then stop for exact approval. The initial analysis request is never approval.

Production consumes the approved immutable snapshot and one ordered `LayoutPlan`. Markdown, HTML, and PDF use the same ordered blocks. Missing fonts, renderer errors, stale hashes, empty PDFs, invalid evidence, or incomplete publication are failures; never write a Vault template through filesystem fallback or return a placeholder. Unsupported reproduction requirements must be disclosed in preview rather than promised as pixel-perfect output.

Implementation entry points are `analyze_template_sources.py`, `build_template_candidate.py`, `validate_template_candidate.py`, and `render_template_preview.py` for candidate preparation. Register with `register_custom_template.register_candidate` only after exact candidate ID approval. Resolve the approved snapshot with `resolve_custom_template.resolve_template`. Compile the production blocks with `layout_plan.compile_layout_plan`. For production, call `finalize_custom_publication.finalize_custom_publication` directly with the exact selected version, Vault destination, and optional desktop destination; it already invokes the renderer. For render-only work, use `render_custom_manuscript.render_custom_manuscript` instead. Do not call both in sequence on the same version because the renderer refuses existing output files. These modules expose Python functions; inspect their signatures instead of inventing CLI flags.

The generic blog exporter does not accept custom manuscript packages. Report the actual custom output folder and separate Vault/desktop outcomes. If no template is named for a manuscript request, ask which approved template to use; if none exists, offer sample analysis and stop at the preview before registration. Existing user outputs remain intact.

## Exact approval and version binding

In the Python examples, `runtime_config` means the Local REST settings file path resolved from the installed runtime JSON's `restDataPath`. This legacy parameter name does **not** mean pass `runtime.json` itself. Read that configured path without printing its API key or certificate. Missing/invalid settings require connection diagnosis, never guessed paths or filesystem fallback.

1. Render a neutral synthetic preview with `render_template_preview.render_preview`. Require successful rendering and registration-ready validation; `needs_review` is not approval.
2. Obtain `H = register_custom_template.candidate_validation_hash(candidate_dir)`. This validates and hashes the exact four-file snapshot. Do not invent a hash or use only a template/PDF hash.
3. Call `template_candidate_state.activate_candidate(conversation_key, candidate_id, H, root=state_root)`. Use the exact active thread ID and `state_root = os.environ.get('CODEX_OBSIDIAN_STATE_ROOT')` (unset means `None`). Show the same unchanged snapshot's preview and stop for approval.
4. After approval, load active state and recompute H. Require the active ID, exact user-approved ID and unchanged hash to match. Changed bytes require a new candidate and preview/approval, not reactivation to reuse old consent.
5. Call `approve_candidate(conversation_key, candidate_id, H, root=state_root)`, then register:

```python
registered = register_custom_template.register_candidate(
    runtime_config=runtime_config,
    candidate_dir=candidate_dir,
    approval={
        'conversation_key': conversation_key,
        'candidate_id': candidate_id,
        'approved_candidate_id': approved_candidate_id,
        'validation_hash': H,
        'status': 'preview_ready',
    },
)
snapshot = resolve_custom_template.resolve_template(
    runtime_config, candidate_id, version=registered['version'],
)
```

Persisted candidate state is `approved`; the registration request separately says `preview_ready`. Use installed HTTPS REST, never a test transport in production. Successful registration allocates immutable `t0.N` and returns `registered`, `version`, `remote_root` after byte readback.

For an existing template, resolve the selected name/ID and retain returned `template_id` and `version` throughout production. Require `snapshot_verified`. Approval belongs to the registry, not a caller-edited status in template JSON. Preserve its component sequence, page and style contract; there is no fixed Step or image count.

## Image and table data

Generate after block content is final, using Codex built-in image generation. Inspect the actual image with `view_image`; follow shared visual-quality/privacy rules. Retry once on failure; a second failure stops production. Do not call generated scenes actual captures.

Custom input is `data['assets']`, not the blog manifest schema:

```python
data['assets'] = [{
    'id': asset_id, 'path': safe_relative_input_path, 'sha256': lowercase_sha256,
    'editorial_review': {
        'method': 'generated_scene', 'prompt': sanitized_generation_prompt,
        'visual_kind': 'result_preview', 'privacy_status': 'cleared',
        'quality_review': {
            'relevant': True, 'professional': True, 'legible': True,
            'artifact_free': True, 'no_generic_ai_motifs': True,
            'note': concise_actual_review,
        },
    },
}]
```

Allowed visual kinds are `ui_screen`, `work_product`, `workflow_diagram`, `result_preview`, `field_scene`. Record actual review, not automatic true flags. Prompts/notes must contain no secrets, personal paths, URLs or source prose. Include the review for generated production images; lower-level synthetic render tests may omit it.

Image blocks use `component: image`, `asset_id`, `alt`, `caption`. Every asset must be referenced. Pass explicit trusted local `asset_root`; input paths are relative underneath it, never absolute/URL/Vault paths. Image bytes, format, decoding, limits and hashes are checked. Output is `assets/<sha256>.<extension>`, with captions below. `quick_table` blocks take `headers` and rectangular `rows` of strings.

Custom output preserves safe asset bindings and supplied editorial reviews in `custom-validation.json`. Do not insert blog `asset-manifest.json`. Automatic checks validate records/bytes, not visual beauty, accuracy or privacy clearance: Codex must perform that review. Dimensions follow the approved template, not blog minimums.

## Finalize once and report both destinations

Choose an absent local `v0.N`, exact matching Vault-relative `/v0.N`, and a new desktop result folder, not the existing publication-library root. Source and destination must not overlap. Pass the original data dictionary including assets, not serialized LayoutPlan output that omits input bindings.

```python
report = finalize_custom_publication.finalize_custom_publication(
    data=data, output_root=new_local_version,
    desktop_root=new_desktop_destination, runtime_config=runtime_config,
    vault_relative_version_dir=exact_vault_version,
    template_name=snapshot['template_id'], template_version=snapshot['version'],
    asset_root=trusted_asset_root,
)
```

Always pass `template_version` for selected-template production; omission selects latest at resolution. The finalizer binds the template, checks layout/assets during rendering, writes package validation, then attempts Vault and desktop. Upload validation checks exact bytes against the pinned registry and a fresh deterministic render. Do not render first and finalize the same version.

Early resolution/input/render failure aborts; it is not offline publication success. A caught Vault publication failure can still permit verified desktop export. Final statuses are `finalized`/`finalized_with_failure`, with separate `vault_publication_status` and `desktop_export_status`. Both destinations requested means success requires `published` and `exported`; `not_attempted` is not a save. Report partial success and actual folder links. Report file names are relative to output_root. Keep failed/existing versions intact; retry with a fresh version.
