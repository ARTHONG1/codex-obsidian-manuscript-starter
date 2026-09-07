# Beginner One-Prompt Remaining Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete and publicly prove a Windows installation path in which a beginner with only Codex installed can install Obsidian, create a dedicated Vault, enable pinned loopback-only Local REST, install both Codex skills, pass doctor, and immediately use `obsidian-manuscript-publisher` without entering a shell command or handling secrets.

**Architecture:** Finish the product as four chained trust boundaries: immutable GitHub release acquisition, atomic Codex skill installation, resumable Windows/Obsidian setup, and doctor-verified publisher activation. Automated tests prove deterministic and hostile-input behavior; a disposable clean-Windows acceptance run proves the actual Codex/Obsidian interaction before merge, tag, and public release.

**Tech Stack:** Windows PowerShell 5.1, PowerShell 7 test host, Python 3.12, `unittest`, Pester 3-compatible tests, GitHub Actions, SHA-256, Authenticode, Obsidian Local REST API 5.0.2, Codex skills/plugins.

## Verified Starting Point

- Worktree: `.worktrees/v052-full-remediation`, branch `codex/v052-full-remediation`.
- Local HEAD: `2a9f16d84aabc358b7b3af79994b263abc7064d6`; clean tracked worktree.
- Local branch is nine commits ahead of its remote branch.
- Draft PR #6 is open and unstable because it still points to the old remote head.
- Public latest release is `v0.5.1`; `v0.5.2` does not exist publicly.
- Task 1 is complete: focused installer-scenario Pester tests pass 9/9.
- Task 2 core is present: focused acquisition/package tests pass, but annotated-tag dereference and explicit tampering regressions remain.
- Task 3-8 primary implementation files are absent.
- `ci/run-all-tests.ps1` is not yet a valid release gate in the current host because it failed to emit evidence and left child test processes running.
- Recovery backup: `C:/Users/user/Documents/ai agent/backups/beginner-one-prompt-20260815-094256`.

## Global Constraints

- Preserve archive, exact conversation deletion, `book_a4`, `adaptive_blog`, `custom_manuscript`, image generation, Local REST byte verification, immutable manuscript versions, and Desktop publication behavior.
- Never install or execute branch-head content. Verify the exact owner/repository, stable tag, final commit, manifest, archive digest, member allowlist, and member hashes before extraction or execution.
- Never print or persist API keys, certificate bodies, tokens, personal Vault content, conversation text, or private absolute paths in tests, logs, release assets, PRs, or acceptance evidence.
- Use only `https://127.0.0.1:<validated-port>` with redirects disabled. Do not enable HTTP or external interfaces.
- Do not overwrite or delete an existing Vault, plugin, skill, publication folder, or user file. Back up exact skill destinations and roll back both skills together on failure.
- Every production change follows RED → GREEN → REFACTOR and a focused commit.
- Each task requires a fresh implementer, a specification reviewer, and a code/security reviewer. Accepted findings receive a failing regression test before a fix.
- No push until local focused gates pass. No merge/tag/release until CI, security review, clean-Windows evidence, and public-redownload verification pass.

---

### Task 1: Close the immutable-release trust boundary

**Files:**
- Modify: `bootstrap/release-acquisition.psm1`
- Modify: `ci/verify-release.ps1`
- Modify: `tests/ReleaseAcquisitionContract.Tests.ps1`
- Modify: `tests/test_release_package.py`

**Interfaces:**
- `Resolve-StableRelease -Repository <owner/name>` returns an exact stable `Tag` and final 40-character commit SHA.
- `Get-VerifiedRelease -Release <object> -DownloadRoot <owned-root>` returns `ReleaseRoot` only after bidirectional manifest/member equality and all hashes pass.

- [ ] **Step 1: Write RED tests for annotated and lightweight tags.** Inject GitHub API responses so a lightweight ref resolves directly to a commit and an annotated tag dereferences tag objects until a commit is reached. Reject cycles, non-commit terminal objects, repository/tag mismatch, and more than four dereference hops.
- [ ] **Step 2: Write RED tampering tests.** Reject one modified ZIP member, one extra manifest entry, one missing manifest entry, duplicate/case-colliding names, metadata URLs outside the exact repository/tag release path, stale `.partial` files, and failed extraction residue.
- [ ] **Step 3: Implement bounded tag dereference and exact member verification.** Keep redirects disabled for identity metadata; dispose hash objects/streams deterministically; clean only installer-owned partial and extraction roots.
- [ ] **Step 4: Run focused gates.**

```powershell
./ci/run-pester-tests.ps1 -Path @((Resolve-Path ./tests/ReleaseAcquisitionContract.Tests.ps1).Path) -ExpectedSkipCount 0
& 'C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m unittest tests.test_release_package tests.test_release_privacy_contract -v
```

Expected: failures 0, errors 0, skips 0.

- [ ] **Step 5: Commit.** Commit message: `fix: complete immutable release verification`.

---

### Task 2: Install both Codex skills atomically with rollback

**Files:**
- Create: `bootstrap/lib/CodexSkills.psm1`
- Create: `bootstrap/install-codex-skills.ps1`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-setup/SKILL.md`
- Create: `tests/CodexSkillBootstrap.Tests.ps1`
- Modify: `tests/test_skill_sync.py`
- Modify: `ci/release-allowlist.txt`

**Interfaces:**
- `Install-VerifiedCodexSkills -ReleaseRoot <path> -CodexSkillsRoot <path> -ReleaseManifest <object>` returns `Status`, `Version`, `InstalledSkills`, `BackupRoots`, and `RestartRequired`.
- The pair `obsidian-manuscript-setup` and `obsidian-manuscript-publisher` is one transaction.

- [ ] **Step 1: Write RED tests** for fresh install, exact idempotent reinstall, existing-version backup, pair-incomplete source, manifest mismatch, destination reparse point, case collision, failure after first promotion, rollback of both destinations, and post-promotion exact parity.
- [ ] **Step 2: Implement staging and pairwise atomic promotion.** Stage below the resolved skills parent, reject links/reparse points, verify every staged hash, rename exact destinations to GUID backups, promote both, verify parity, and restore both on any failure.
- [ ] **Step 3: Make the setup skill the continuation entrypoint.** It must recognize the initial installation request and the exact resume sentence, read only non-secret state, and never require `codex plugin` CLI availability.
- [ ] **Step 4: Run focused gates.**

```powershell
./ci/run-pester-tests.ps1 -Path @((Resolve-Path ./tests/CodexSkillBootstrap.Tests.ps1).Path) -ExpectedSkipCount 0
& 'C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m unittest tests.test_skill_sync -v
```

- [ ] **Step 5: Commit.** Commit message: `feat: bootstrap Codex skills atomically`.

---

### Task 3: Provide safe no-WinGet prerequisite installation

**Files:**
- Create: `bootstrap/lib/OfficialInstallers.psm1`
- Modify and byte-mirror: `bootstrap/dependencies.lock.json`, `dependencies.lock.json`, `plugins/obsidian-manuscript-publisher/bootstrap/dependencies.lock.json`
- Modify and byte-mirror: `bootstrap/install-windows.ps1`, `plugins/obsidian-manuscript-publisher/bootstrap/install-windows.ps1`
- Create: `tests/OfficialInstallerContract.Tests.ps1`
- Modify: `tests/PythonRuntimeContract.Tests.ps1`, `tests/InstallerContract.Tests.ps1`, `tests/test_dependency_contract.py`, `THIRD_PARTY_NOTICES.md`

**Interfaces:**
- `Install-PinnedOfficialApplication -Application Python|Obsidian -DependencyLock <object> -DownloadRoot <owned-root> -ProcessRunner <scriptblock>` returns `Status`, `Version`, `RestartRequired`, and `Executable`.

- [ ] **Step 1: Add RED tests** for WinGet preference, WinGet absence, official HTTPS URL, exact SHA-256, expected Authenticode signer, per-user silent arguments, interrupted download, digest/signature mismatch, nonzero exit, restart-required exit, and post-install rediscovery.
- [ ] **Step 2: Resolve current official installers from primary vendor sources in a maintainer-only temporary directory.** Record exact version, URL, SHA-256, Authenticode subject/issuer, product name, and silent arguments. Do not commit installer binaries.
- [ ] **Step 3: Implement verified fallback.** Use `.partial` downloads, SHA-256 and Authenticode before execution, argument arrays, bounded process waits, and no global PATH mutation.
- [ ] **Step 4: Verify lock-copy byte identity and notices.** Run focused Pester plus `tests.test_dependency_contract`; require zero skips.
- [ ] **Step 5: Commit.** Commit message: `feat: install pinned prerequisites without winget`.

---

### Task 4: Implement schema-v3 resumable setup and safe default paths

**Files:**
- Create: `bootstrap/lib/BootstrapState.psm1`
- Modify/mirror: `bootstrap/lib/Environment.psm1`, `bootstrap/install-windows.ps1`, and matching plugin bootstrap files
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-setup/SKILL.md`
- Create: `tests/BootstrapStateContract.Tests.ps1`
- Modify: `tests/InstallerContract.Tests.ps1`

**Interfaces:**
- State schema 3 stores `schemaVersion`, release/tag/commit, `lastCompletedStage`, approved paths, installed versions, and hashes only.
- `Get-BootstrapState`, `Save-BootstrapState`, `Test-BootstrapStage`, and `Get-NextBootstrapStage` probe real state before each transition.

- [ ] **Step 1: Add RED tests** for every approved stage, atomic writes, truncated state, schema-v2 migration, stale-marker recovery, restart after Python/skills/Obsidian, idempotent rerun, no secret-like keys, and numbered empty Vault selection on collision.
- [ ] **Step 2: Implement real-probe resume.** A marker is a hint only. Resume at the first failed real probe and never repeat a successful mutation.
- [ ] **Step 3: Implement one consolidated consent.** Before consent, only verified temporary downloads may exist. After approval, install Obsidian, create the dedicated Vault, and enable pinned Local REST.
- [ ] **Step 4: Run BootstrapState and Installer contracts with zero failures/skips.**
- [ ] **Step 5: Commit.** Commit message: `feat: resume beginner installation safely`.

---

### Task 5: Make doctor the only readiness authority

**Files:**
- Modify/mirror: `bootstrap/lib/Vault.psm1`, `LocalRest.psm1`, `PublicationLibrary.psm1`, `doctor.ps1`, `install-windows.ps1`
- Create: `bootstrap/publisher-manifest.json`
- Create: `tests/BeginnerDoctorContract.Tests.ps1`
- Modify: `tests/InstallerContract.Tests.ps1`, `tests/test_local_rest_security.py`

**Interfaces:**
- Doctor emits `status`, `releaseVersion`, `vaultStatus`, `restStatus`, `roundTripStatus`, `publisherStatus`, and `publicationLibraryStatus` without secrets.
- Overall `status` is `ready` only when all subordinate statuses are `ready`.

- [ ] **Step 1: Add RED tests** for delayed/partial Local REST settings, valid port bounds, HTTPS-only loopback, redirect rejection, secret non-output, byte-identical create/read/delete, publisher manifest mismatch, publication root validation, and prohibition of direct Vault-write fallback.
- [ ] **Step 2: Build and verify the publisher manifest.** Compare exact membership and hashes after skill promotion.
- [ ] **Step 3: Implement bounded Obsidian launch/readiness.** Do not claim success on timeout; return the exact resume sentence.
- [ ] **Step 4: Run doctor, installer, Local REST, archive, publish, export, and delete isolation regressions.**
- [ ] **Step 5: Commit.** Commit message: `feat: verify Obsidian and publisher readiness`.

---

### Task 6: Rebuild the beginner-facing documentation contract

**Files:**
- Modify: `README.md`, `INSTALL_PROMPT.md`, `docs/INSTALL_GUIDE.md`, `docs/TROUBLESHOOTING.md`, `docs/USAGE_GUIDE.md`, `docs/RELEASE.md`
- Modify: `tests/test_documentation_contract.py`, `tests/test_obsidian_manuscript_workspace.py`

- [ ] **Step 1: Add RED tests** requiring one canonical Korean installation request, one canonical resume sentence, consolidated consent wording, no required shell/API-key/certificate steps, no fixed-time promise, three first-use requests, valid links, and no claim that unpublished `v0.5.2` is already public.
- [ ] **Step 2: Put the beginner flow first.** README order: what it does → copyable request → what Codex changes → consent → restart/resume → first use → recovery → advanced/developer material.
- [ ] **Step 3: Make release wording state-aware.** Before publication say “next verified stable release”; only the final release commit may name public `v0.5.2` installation URLs.
- [ ] **Step 4: Run documentation tests with zero failures/skips.**
- [ ] **Step 5: Commit.** Commit message: `docs: make one-prompt installation beginner first`.

---

### Task 7: Build acceptance evidence and repair aggregate CI lifecycle

**Files:**
- Create: `acceptance/windows/acceptance-schema.json`, `validate-evidence.py`, `README.md`
- Create: `ci/run-beginner-install-acceptance.ps1`
- Modify: `ci/run-all-tests.ps1`, `ci/run-python-tests.ps1`, `.github/workflows/windows-ci.yml`, `ci/build-release.ps1`, `ci/verify-release.ps1`, `ci/release-allowlist.txt`
- Create: `tests/BeginnerAcceptanceContract.Tests.ps1`, `tests/test_acceptance_evidence.py`
- Modify: `tests/TestRunnerContract.Tests.ps1`, `tests/SecretScan.Tests.ps1`, `tests/test_ci_contract.py`, `tests/test_release_package.py`, `tests/test_release_privacy_contract.py`

- [ ] **Step 1: Add RED lifecycle tests** proving child test processes terminate, stdout/stderr are bounded, evidence JSON is written on success and failure, temporary files are removed, and aggregate exit codes preserve the first failing gate.
- [ ] **Step 2: Add RED acceptance tests** rejecting extra terminal interactions, secrets, personal paths, release mismatch, missing doctor round trip, missing archive/publish/export/delete smoke, and neighboring-sentinel deletion.
- [ ] **Step 3: Implement sanitized evidence and isolated product smoke.** Fake destructive branches use only temporary roots; real acceptance records no Vault contents or personal paths.
- [ ] **Step 4: Integrate CI dependencies.** Package must depend on contracts, installer matrix, Python, Pester, privacy, parity, and acceptance-schema validation. Generated artifacts come only from a clean tracked source and contain no user data.
- [ ] **Step 5: Run the aggregate gate twice.** Both runs must emit evidence, terminate all children, report Python failures/errors 0 with exactly four documented environment skips, and Pester failures/skips 0.
- [ ] **Step 6: Build twice and compare every ZIP member and hash; verify both in fresh roots.**
- [ ] **Step 7: Commit.** Commit message: `ci: gate release on reproducible beginner acceptance`.

---

### Task 8: Independent review, local promotion, and disposable Windows acceptance

**Files:**
- Record: `.planning/beginner-one-prompt-implementation/review-report.md`
- Use: `verify_skill_sync.py`; do not commit installed-skill backups or acceptance Vaults.

- [ ] **Step 1: Dispatch nine read-only audits:** release trust, skill rollback, official installers, state resume, Local REST secrecy/TLS, path/reparse handling, CI reproducibility, beginner UX, and adversarial overall review.
- [ ] **Step 2: Reproduce every P0/P1/installation-affecting P2.** Add a failing test before each accepted fix; rerun focused and aggregate suites.
- [ ] **Step 3: Require zero unresolved P0/P1/installation-affecting P2.** Document nonblocking P3 without weakening tests.
- [ ] **Step 4: Back up and promote both local installed skills together.** Verify exact source/destination membership and hashes; run fake-release/fake-REST smoke; restore both backups on failure.
- [ ] **Step 5: Run disposable clean-Windows scenarios.** Minimum release blockers: Windows 11 Codex-only primary flow, no-WinGet fallback, restart resume, default-path collision, interrupted download, tampered archive, delayed Local REST, and existing-skill upgrade/rollback.
- [ ] **Step 6: Validate sanitized evidence.** The primary flow permits only initial paste, consolidated consent, and requested restart continuation. Any extra terminal command is a failure.

If no disposable Windows Sandbox/VM/fresh account is available, stop before merge/tag/release and report this exact external evidence blocker. Do not substitute the developer machine's existing configured environment.

---

### Task 9: Push, merge, tag, release, and public reinstall verification

**Files:**
- Finalize only verified version metadata, release notes, README/install prompt release references, manifests, and checksums.

- [ ] **Step 1: Confirm authorization and clean state.** Verify `git status`, reviewed HEAD, backup paths, no secret/user-data diff, and exact version identity.
- [ ] **Step 2: Push the branch without force and update Draft PR #6.** Include trust boundaries, test counts, clean-Windows evidence, and known P3 findings.
- [ ] **Step 3: Wait for every required GitHub check.** Fix failures through reviewed commits; do not merge on failed, cancelled, or unexpected skipped checks.
- [ ] **Step 4: Merge the passing reviewed PR and record the merge commit.** Build release assets from that exact commit only.
- [ ] **Step 5: Create annotated tag `v0.5.2` once and publish verified assets:** ZIP, `release-manifest.json`, `SHA256SUMS`, publisher manifest, release notes, and sanitized acceptance evidence.
- [ ] **Step 6: Redownload every public asset into a fresh root.** Verify tag → final commit, manifest → commit, archive/member hashes, allowlist, privacy scan, and clean extraction.
- [ ] **Step 7: From a fresh Windows account, use only the public README request.** Pass only when doctor reports `ready`, one conversation is archived, one A4 Desktop bundle is published, and deletion removes only the exact test bundle.
- [ ] **Step 8: Mark `v0.5.2` latest and report exact evidence.** Never move the tag.

## Final Completion Definition

Completion requires all of the following simultaneously:

1. Focused and aggregate local gates pass with stated skip counts and no orphan processes.
2. Source and packaged bootstrap/skills are byte-identical where required.
3. Independent review has zero unresolved P0/P1/installation-affecting P2.
4. Both installed local skills match the reviewed source and pass smoke tests.
5. Disposable clean-Windows evidence validates every required scenario.
6. Draft PR #6 CI is fully green and merged without force push.
7. Public `v0.5.2` assets are redownloaded and independently reverified.
8. The public README request succeeds from a fresh Windows account without terminal/API-key/path handling.

Anything less is a release candidate, not a completed beginner one-prompt installation release.
