# Beginner One-Prompt Final Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` for inline implementation. Use subagents only for time-bounded, read-only review. Steps use checkbox syntax for recovery after context loss.

**Goal:** Finish the remaining Windows beginner installation path from the verified release-acquisition baseline, prove it on disposable Windows, and publish `v0.5.2` only when the public README request works without shell/API-key/path handling.

**Architecture:** Keep the four trust boundaries separate: immutable release, atomic Codex skill pair, resumable Windows/Obsidian setup, and doctor-gated publisher activation. Implement sequentially in the current worktree. Reviewers inspect completed diffs but do not own the critical path; if a reviewer does not return within three bounded waits, the controller records the timeout, performs the documented local review, and continues.

**Tech Stack:** Windows PowerShell 5.1, PowerShell 7 orchestration, Python 3.12, Pester 3-compatible tests, Python `unittest`, GitHub Actions, SHA-256, Authenticode, Obsidian Local REST API 5.0.2.

## Verified Baseline

- Branch: `codex/v052-full-remediation`.
- HEAD: `6b7ef1bcf36a91937de7584d8845d2f657756840`.
- Public latest release: `v0.5.1`; public `v0.5.2` does not exist.
- Task 1 installer scenarios: 9/9 passed.
- Task 2 release acquisition: 11/11 passed on the latest local rerun; one reviewer observed a prior 10/11 cleanup-mock flake, so repeatability is a prerequisite.
- Python release/package and CI contracts: 15/15 passed.
- Existing backup: `C:/Users/user/Documents/ai agent/backups/beginner-one-prompt-20260815-094256`.
- Remaining high-impact defects: bootstrap copy drift, missing skill-pair bootstrap, missing no-WinGet verified installers, incomplete resumable state, doctor not authoritative, aggregate runner evidence/process leak, premature `v0.5.2` documentation.

## Global Constraints

- Preserve all manuscript, blog, custom-template, archive, export, image, and exact-deletion behavior.
- Do not touch real Vault content or Desktop publication output during automated tests.
- Never print or persist API keys, certificate bodies, tokens, conversations, manuscripts, or personal absolute paths.
- Only `https://127.0.0.1:<validated-port>` is allowed for Local REST; no redirect, HTTP, or external binding.
- No branch archives, `irm | iex`, force push, tag movement, or execution before archive/manifest/hash/allowlist validation.
- Existing skills and Vaults are preserved by exact-path backup and all-or-nothing rollback.
- Every production change uses RED → GREEN → REFACTOR, focused verification, and a focused commit.
- No public release claim before clean-Windows evidence and public redownload/reinstall verification.

---

### Task 0: Stabilize the baseline and restore bootstrap parity

**Files:**
- Modify if required: `tests/ReleaseAcquisitionContract.Tests.ps1`
- Mirror: `bootstrap/install-windows.ps1` → `plugins/obsidian-manuscript-publisher/bootstrap/install-windows.ps1`
- Modify: `tests/InstallerContract.Tests.ps1`

- [ ] Run `ReleaseAcquisitionContract.Tests.ps1` five times in separate PowerShell processes. Each run must report 11 passed, 0 failed, 0 skipped. If any run fails, replace shared global mock state with test-local injected downloader callbacks and rerun five times.
- [ ] Add/confirm a failing parity test for the root and packaged installer, copy only the reviewed source installer change, then require byte-identical SHA-256.
- [ ] Run InstallerScenario, ReleaseAcquisition, InstallerContract, Python release-package, and CI contracts.
- [ ] Commit `fix: stabilize release acquisition and bootstrap parity`.

### Task 1: Implement atomic installation of both Codex skills

**Files:**
- Create: `bootstrap/lib/CodexSkills.psm1`
- Create: `bootstrap/install-codex-skills.ps1`
- Create: `tests/CodexSkillBootstrap.Tests.ps1`
- Modify: setup `SKILL.md`, `tests/test_skill_sync.py`, `ci/release-allowlist.txt`

- [ ] Write failing tests for fresh install, exact reinstall, pair-incomplete source, hash mismatch, case collision, reparse destination, backup, first-promotion failure, two-skill rollback, and exact post-promotion parity.
- [ ] Implement `Install-VerifiedCodexSkills -ReleaseRoot -CodexSkillsRoot -ReleaseManifest` as one two-skill transaction using sibling staging and GUID backups.
- [ ] Make setup skill recognize the initial request and exact resume sentence without depending on `codex plugin` CLI.
- [ ] Run focused Pester and `tests.test_skill_sync`; require zero failures/skips.
- [ ] Commit `feat: bootstrap Codex skills atomically`.

### Task 2: Implement verified prerequisites and schema-v3 restart recovery

**Files:**
- Create: `bootstrap/lib/OfficialInstallers.psm1`, `bootstrap/lib/BootstrapState.psm1`
- Modify/mirror: dependency locks, installer, Environment and PythonRuntime modules
- Create: `tests/OfficialInstallerContract.Tests.ps1`, `tests/BootstrapStateContract.Tests.ps1`
- Modify: runtime/installer/dependency tests and `THIRD_PARTY_NOTICES.md`

- [ ] Add failing tests for WinGet preference, no-WinGet official fallback, HTTPS/SHA-256/Authenticode/silent arguments, interrupted download, restart exits, and post-install rediscovery.
- [ ] Resolve exact official Python 3.12 x64 and Obsidian x64 installer metadata from primary vendor sources; commit only URL/version/hash/signer/arguments, never binaries.
- [ ] Implement verified `.partial` acquisition and bounded process execution with no global PATH changes.
- [ ] Add schema-v3 tests for every stage, atomic writes, schema-v2 migration, truncated/stale state, restart after skills/Python/Obsidian, numbered empty Vault collision, idempotency, and secret-key rejection.
- [ ] Implement real-probe resume; stage markers are hints, not proof.
- [ ] Require byte-identical locks and bootstrap copies; run all focused tests with zero failures/skips.
- [ ] Commit `feat: install prerequisites and resume setup safely`.

### Task 3: Make doctor the sole readiness authority

**Files:**
- Modify/mirror: Vault, LocalRest, PublicationLibrary, doctor, installer
- Create: `bootstrap/publisher-manifest.json`, `tests/BeginnerDoctorContract.Tests.ps1`
- Modify: Local REST and publisher regression tests

- [ ] Add failing tests for delayed/partial configuration, port bounds, HTTPS-only loopback, redirects, secret non-output, byte-identical create/read/delete, manifest mismatch, publication-root safety, and no filesystem fallback.
- [ ] Generate and verify exact publisher membership/hashes.
- [ ] Make `ready` reachable only after doctor round trip and publisher verification. Pre-doctor status must explicitly request Obsidian launch/resume.
- [ ] Run doctor, archive, publish, Desktop export, and exact deletion regressions.
- [ ] Commit `feat: gate publisher activation on doctor`.

### Task 4: Repair beginner UX, acceptance evidence, and aggregate CI

**Files:**
- Modify: README, INSTALL_PROMPT, install/troubleshooting/usage/release docs
- Create: `acceptance/windows/*`, `ci/run-beginner-install-acceptance.ps1`
- Modify: `ci/run-all-tests.ps1`, child runners, workflow, package/verification scripts
- Create/modify: documentation, acceptance, runner, CI, privacy, release tests

- [ ] Add documentation tests for one canonical install request, one resume sentence, one consolidated consent, no shell/API-key/certificate handling, `requirements.lock.txt`, three first-use requests, valid links, and no unpublished-version claim.
- [ ] Add runner lifecycle tests requiring evidence JSON on success and runner-level failure, bounded stdout/stderr, deterministic exit code, all child-process cleanup, and repository-root evidence location.
- [ ] Add acceptance evidence schema tests rejecting secrets, personal paths, extra interactions, release mismatch, missing doctor/archive/A4 export/exact deletion, and deleted sentinel notes.
- [ ] Implement CI package dependencies so no package is built before Python, Pester, installer, privacy, parity, and acceptance-schema gates pass.
- [ ] Run aggregate tests twice; both runs must emit valid evidence and leave zero audit-owned child processes.
- [ ] Build two archives and require identical member names and member hashes; verify each in a fresh root.
- [ ] Commit `ci: gate release on beginner acceptance evidence`.

### Task 5: Security review, local promotion, and clean-Windows acceptance

- [ ] Run nine read-only audits: release trust, skill rollback, official installer trust, state resume, Local REST, path/deletion safety, CI reproducibility, beginner UX, adversarial completion claims.
- [ ] Reproduce every P0/P1/installation-affecting P2 with a failing test; fix and re-review. Completion requires zero unresolved blockers.
- [ ] Back up both installed skills, promote them as one transaction, verify exact parity, and run fake-release/fake-REST smoke. Restore both on failure.
- [ ] Run disposable Windows scenarios: Windows 11 Codex-only, no-WinGet, restart resume, path collision, interrupted download, tampered archive, delayed REST, previous-skill upgrade/rollback.
- [ ] Validate sanitized evidence. Primary flow permits only initial paste, consolidated consent, and requested restart continuation.

If no disposable fresh Windows environment is available, stop at a verified local release candidate. Do not merge, tag, or release.

### Task 6: GitHub merge and immutable public release

- [ ] Confirm explicit GitHub deployment authorization, clean tracked state, reviewed HEAD, backups, no secret/user-data diff, and consistent version metadata.
- [ ] Push without force, update Draft PR #6, and wait for every required check. Fix any failed/cancelled/unexpected-skipped check with a reviewed commit.
- [ ] Merge only after clean-Windows evidence passes; record merge commit.
- [ ] Rebuild assets from the merge commit, create annotated `v0.5.2` once, and publish ZIP, manifest, checksums, publisher manifest, notes, and sanitized evidence.
- [ ] Redownload all public assets into a new root and verify tag→commit→manifest→archive→member hashes.
- [ ] From a fresh Windows account, use only the public README request and verify doctor, conversation archive, A4 Desktop export, and exact bundle deletion.
- [ ] Mark `v0.5.2` latest only after the public reinstall succeeds.

## Completion Definition

The work is complete only when all focused/aggregate/CI tests pass with declared skip counts, no orphan process remains, source/package/installed parity is exact, independent review has no blocker, disposable Windows evidence passes, PR #6 is green and merged, public assets are reverified, and a fresh account succeeds using only the README request.
