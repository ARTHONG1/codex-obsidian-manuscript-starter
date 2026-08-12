# v0.4.0 release notes

## Fixed

- Book V3 now uses its own canonical data model and native HTML/PDF renderers.
- Desktop publication correctly preserves V3 array-based quick-reference rows,
  string Step and tip bodies, preparation panels, and optional real-world panels.
- Publication finalization runs validation, rendering, Vault publication attempt,
  and Desktop export in one deterministic order while reporting Vault and Desktop
  outcomes separately.
- The packaged plugin now contains the same pinned rendering requirements as the
  repository checkout.

## Installation and safety

- All beginner-facing installation references now point to the immutable `v0.4.0`
  release.
- Installation continues to require explicit consent for the HTTPS loopback-only
  Obsidian Local REST API community plugin.
- Existing Vaults, Local REST settings, conversation bundles, and historical
  manuscript versions are never overwritten by this release.

## Verification

- V3 tests force V2 renderer entry points to fail, proving V3 does not use the
  legacy renderer path.
- Export, publication, source-boundary, and existing V1/V2/blog regressions are
  covered by the release verification suite.
