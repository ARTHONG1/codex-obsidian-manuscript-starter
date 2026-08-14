# Public release checklist

This checklist is for the repository maintainer, not first-time users.

1. Run `git status --short` and confirm that no Vault, `data.json`, certificate, private key, manuscript output, or local runtime file is present.
2. Run `ci/run-all-tests.ps1 -PythonPath $Python312 -ExpectedPythonSkipCount 4` from Windows PowerShell 5.1 with the managed Python 3.12 executable. Review `artifacts/test-evidence.json`; the runners decide success from explicit result counts and expected skip counts.
3. Run `python -m pip install -r requirements-dev.txt`, then run the plugin validator against `plugins/obsidian-manuscript-publisher`.
4. The aggregate runner executes the manuscript Python suite with the Codex bundled Python 3.12 runtime and records path-neutral evidence.
5. Download the pinned Windows CPython 3.12 wheelhouse without committing the wheels, then run `$env:TASK1_REQUIRE_REAL_WHEELHOUSE='1'; $env:TASK1_REAL_WHEELHOUSE='C:\path\to\wheelhouse'; python -m unittest tests.test_dependency_contract.RuntimeLockGeneratorTests.test_real_wheelhouse_recreates_committed_lock_when_provided`. This gate must pass; an unset wheelhouse is only acceptable for offline unit tests, not release evidence.
6. In a clean Windows profile, test the explicit-consent path: install Obsidian, create a new Vault, install the pinned plugin, open Obsidian, run doctor, archive one conversation, synthesize one manuscript, and delete that conversation bundle.
7. Confirm that doctor fails safely when Obsidian is closed and never triggers direct Vault filesystem publication.
8. Confirm the public author/brand wording, `CITATION.cff`, `THIRD_PARTY_NOTICES.md`, and non-affiliation wording before publishing.
9. Build `codex-obsidian-manuscript-starter-v0.5.2.zip` with `ci/build-release.ps1`, then run `ci/verify-release.ps1` against a new temporary install root. Publish SHA-256 values for release assets and verify the tag points to the reviewed commit.
10. Test the README commands from a clean checkout using `--ref v0.5.2`; do not publish a dirty working tree or planning/Vault artifacts.

The release builder obtains candidates from `git ls-files`, applies `ci/release-allowlist.txt`, rejects untracked required files, and excludes source documents, generated outputs, caches, credentials, and user data. The verifier reads every ZIP member before extraction, checks normalized paths and case collisions, validates the checksum and v0.5.2 bootstrap identity, and performs a clean temporary extraction.

The current four legitimate Python skips are `test_real_wheelhouse_recreates_committed_lock_when_provided` when no real wheelhouse is supplied, `test_existing_item_reparse_point_is_rejected_when_supported`, `test_rejects_reparse_point_without_following_it_when_supported`, and `test_snapshot_rejects_reparse_staging_parent_when_supported` when the Windows profile cannot create the required reparse point. The aggregate runner must receive exactly `-ExpectedPythonSkipCount 4`; any mismatch remains a release failure.
