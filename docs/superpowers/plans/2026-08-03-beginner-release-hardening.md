# Beginner Release Hardening Implementation Plan

> **For agentic workers:** Use this plan task-by-task with verification after every task.

**Goal:** Make the Windows beginner installation resumable, dependency-aware, reproducible, and legally/brand documented before the v0.3.0 GitHub release.

**Architecture:** Keep the existing PowerShell bootstrap and Python publication pipeline. Add explicit dependency detection and durable stage markers; keep Vault writes non-destructive. Separate project copyright, third-party notices, brand attribution, and non-affiliation language. Pin installation and dependency inputs to immutable release evidence.

**Tech Stack:** PowerShell 5.1, Python, Codex plugin marketplace, Obsidian Local REST API, GitHub Releases.

## Global Constraints

- Do not use `irm | iex` or unverified download scripts.
- Never print API keys, certificates, or private paths in user-facing output.
- Never overwrite a non-empty existing Vault.
- Preserve the existing binary MIME and byte-for-byte readback contract.
- Installation must be safe to rerun after Codex or Obsidian restarts.
- Release only from a clean checkout with a fixed version/ref and passing tests.

---

### Task 1: Dependency preflight and recovery contract

**Files:**
- Modify: `bootstrap/lib/Environment.psm1`
- Modify: `bootstrap/install-windows.ps1`
- Modify: `bootstrap/doctor.ps1`
- Modify: packaged copies under `plugins/obsidian-manuscript-publisher/bootstrap/`
- Modify: `README.md`
- Test: `tests/InstallerContract.Tests.ps1`
- Test: `tests/test_dependency_contract.py`

- [ ] Add tests for missing Python, missing Pillow/ReportLab, and successful dependency detection before implementation.
- [ ] Make the bootstrap return deterministic status and a safe rerun command instead of failing with an unexplained dependency error.
- [ ] Use the configured/runtime Python interpreter consistently; do not silently install arbitrary packages from an untrusted source.
- [ ] Document the official Python fallback when the Codex runtime is unavailable.
- [ ] Mirror the bootstrap change into the packaged plugin tree and run the focused tests.

### Task 2: Durable installation stages

**Files:**
- Modify: `bootstrap/install-windows.ps1`
- Modify: `bootstrap/lib/Environment.psm1`
- Modify: `bootstrap/lib/LocalRest.psm1`
- Modify: `bootstrap/lib/Vault.psm1`
- Modify: packaged copies under `plugins/obsidian-manuscript-publisher/bootstrap/`
- Test: `tests/InstallerContract.Tests.ps1`

- [ ] Add a runtime-local stage file containing only non-secret status and schema version.
- [ ] Record `preflight`, `dependency_ready`, `vault_ready`, `local_rest_ready`, `runtime_ready`, and `doctor_verified` only after each stage succeeds.
- [ ] On rerun, validate each completed stage before skipping it; stale or malformed state must be discarded safely.
- [ ] Add interruption/restart tests at each boundary and verify no existing Vault content is overwritten.

### Task 3: Reproducible release and legal/brand documentation

**Files:**
- Modify: `README.md`
- Modify: `plugins/obsidian-manuscript-publisher/.codex-plugin/plugin.json`
- Modify: `.agents/plugins/marketplace.json`
- Create: `THIRD_PARTY_NOTICES.md`
- Create: `CITATION.cff`
- Create: `SECURITY.md`
- Modify: `docs/RELEASE.md`
- Modify: `LICENSE` only after the confirmed public copyright name is available
- Test: `tests/test_documentation_contract.py`
- Test: `tests/SecretScan.Tests.ps1`

- [ ] Add project attribution, AI찬우쌤 attribution, classddok.com introduction, and explicit OpenAI/Codex/Obsidian non-affiliation language.
- [ ] Record Local REST API, Pillow, and ReportLab versions, licenses, copyright notices, and upstream links.
- [ ] Add release checklist for immutable tag/ref, checksums, clean checkout, and artifact allowlist.
- [ ] Add manifest homepage, repository, license, keywords, and author metadata without inventing legal facts.
- [ ] Keep private paths, runtime settings, certificates, and keys outside release artifacts.

### Task 4: Verification and release gate

**Files:**
- Modify: `docs/RELEASE.md`
- Test: all existing Python and PowerShell suites
- Create: release verification notes under `.planning/` only

- [ ] Run Python full suite, InstallerContract, SecretScan, dependency contract, and `git diff --check`.
- [ ] Build a clean checkout from the release candidate and run the documented installation contract without modifying the current Vault.
- [ ] Verify release artifact file allowlist, SHA-256, secret scan, and license notice presence.
- [ ] Verify current GitHub remote and branch before publishing.

### Task 5: Commit, tag, and publish

**Files:**
- Stage only reviewed product, test, and release documentation files.

- [ ] Review `git diff --cached` and exclude planning records, local outputs, and unrelated changes.
- [ ] Commit with a release-hardening message.
- [ ] Create the version tag only after all verification commands pass.
- [ ] Push the branch/tag and create the GitHub release according to the repository workflow.
- [ ] Recheck the remote commit, tag, release asset hashes, and install instructions after publication.
