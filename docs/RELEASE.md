# Public release checklist

This checklist is for the repository maintainer, not first-time users.

1. Run `git status --short` and confirm that no Vault, `data.json`, certificate, private key, manuscript output, or local runtime file is present.
2. Run the Pester installer and secret-scan suites from the repository root.
3. Run `python -m pip install -r requirements-dev.txt`, then run the plugin validator against `plugins/obsidian-manuscript-publisher`.
4. Run the manuscript Python test suite with the Codex bundled Python runtime.
5. In a clean Windows profile, test the explicit-consent path: install Obsidian, create a new Vault, install the pinned plugin, open Obsidian, run doctor, archive one conversation, synthesize one manuscript, and delete that conversation bundle.
6. Confirm that doctor fails safely when Obsidian is closed and never triggers direct Vault filesystem publication.
7. Confirm the public author/brand wording, `CITATION.cff`, `THIRD_PARTY_NOTICES.md`, and non-affiliation wording before publishing.
8. Create an immutable `v0.3.1` GitHub release only after the above checks pass. Publish SHA-256 values for release assets and verify the tag points to the reviewed commit.
9. Test the README commands from a clean checkout using `--ref v0.3.1`; do not publish a dirty working tree or planning/Vault artifacts.
