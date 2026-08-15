# Beginner One-Prompt Release Finalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. The critical path is inline; subagents are limited to time-bounded read-only review. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Starting from the current verified local branch, finish a safe one-prompt Windows installation that lets a Codex-only beginner install Obsidian, connect Local REST, install both Codex skills, resume after restarts, and use Obsidian Manuscript Publisher without manual shell work.

**Architecture:** The work is a gated chain: owned-process test harness → atomic two-skill installation → verified prerequisites and resumable state → doctor-authoritative readiness → beginner documentation and acceptance evidence → local promotion and disposable-Windows acceptance → optional immutable GitHub release. Each stage consumes machine-readable evidence from the previous stage and cannot advance on warnings, stale evidence, or unowned processes.

**Tech Stack:** Windows PowerShell 5.1/PowerShell 7, Pester 5, Python 3.12, Python `unittest`, GitHub Actions, SHA-256, Authenticode, Windows Job Objects, Obsidian Local REST API over loopback HTTPS.

## Current Baseline

- Worktree: the isolated `v052-full-remediation` worktree of this repository
- Branch: `codex/v052-full-remediation`
- Starting commit: `1ad10d62bc67379b34d7ec3b23996bca0e5c8f0f` or a reviewed successor.
- Completed work that must not be repeated:
  - release identity, exact repository/tag/archive binding, exact member set, and per-member SHA-256 checks;
  - root/package `bootstrap/install-windows.ps1` byte parity;
  - aggregate evidence fallback and repository-root evidence location.
- Public latest at plan time: `v0.5.1`. `v0.5.2` is a local release candidate until the final public reinstall gate passes.
- Backup: the timestamped `beginner-one-prompt-20260815-094256` backup directory outside the release tree
- Backup bundle SHA-256: `3CF3402E46B7F36B1509F0FE8D48845927B66648F3C338016AC75E15AD5086D2`

## Global Constraints

- Preserve all existing Vaults, API keys, certificates, conversations, manuscripts, installed skills, Obsidian settings, and desktop publication files.
- Never fall back from Local REST to direct Vault filesystem writes.
- Never enumerate and terminate arbitrary `python.exe`, `pwsh.exe`, or `powershell.exe` processes. Only terminate processes attached to the current run's owned Windows Job Object.
- Use exact repository identity and immutable release assets. Do not use branch ZIPs, `irm | iex`, moving tags, or unverified remote scripts.
- Installer downloads must use an owned `.partial` path and pass HTTPS URL, exact SHA-256, and expected Authenticode publisher checks before execution.
- Do not log or package API keys, certificate bodies, tokens, personal absolute paths, Vault contents, conversations, manuscripts, source documents, or generated user assets.
- Every production change follows RED → GREEN → REFACTOR, focused regression, source/package parity, secret/path scan, and a focused commit.
- The setup skill and publisher skill are one installation transaction: either both verified versions are active or the exact previous pair is restored.
- `ready` is emitted only by doctor after a real HTTPS create/read/delete round trip and publisher-manifest verification.
- GitHub push, PR update, merge, tag, or release requires explicit same-task authorization containing `GitHub 배포까지 승인`.
- Merge/tag/release additionally requires disposable clean-Windows evidence. A configured development PC is not a substitute.

## File and Interface Map

### New process ownership layer

- Create `ci/lib/OwnedProcess.psm1`.
- Export:
  - `New-OwnedProcessRun -RootPath <string> -Name <string> -> OwnedRun`
  - `Invoke-OwnedProcess -Run <OwnedRun> -Name <string> -FilePath <string> -ArgumentList <string[]> -WorkingDirectory <string> -TimeoutSeconds <int> -> OwnedProcessResult`
  - `Close-OwnedProcessRun -Run <OwnedRun> -> void`
- `OwnedRun` contains `runId`, `runRoot`, `ledgerPath`, and a live Windows Job Object handle configured with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`.
- `OwnedProcessResult` contains `name`, `rootPid`, `exitCode`, `timedOut`, `durationMs`, `stdoutPath`, `stderrPath`, and `operationalFailure`.
- The ledger contains only run-local identifiers and relative artifact paths; it contains no command-line secrets or personal source paths.

### New skill transaction layer

- Create `bootstrap/lib/CodexSkills.psm1`, `bootstrap/install-codex-skills.ps1`, and `bootstrap/codex-skills-manifest.json`.
- Export:
  - `Test-CodexSkillSource -ReleaseRoot <string> -ManifestPath <string> -> VerificationResult`
  - `Install-VerifiedCodexSkillPair -ReleaseRoot <string> -CodexSkillsRoot <string> -ManifestPath <string> -> InstallationResult`
- The manifest names exactly `obsidian-manuscript-setup` and `obsidian-manuscript-publisher`, with every relative member path and SHA-256.

### New prerequisite and state layers

- Create `bootstrap/lib/OfficialInstallers.psm1`.
- Export `Install-VerifiedOfficialPackage -PackageLock <object> -DownloadRoot <string> -InstallRoot <string> -> InstallerResult`.
- Create `bootstrap/lib/BootstrapState.psm1`.
- Export:
  - `Read-BootstrapState -Path <string> -> BootstrapStateV3`
  - `Write-BootstrapStateAtomic -Path <string> -State <BootstrapStateV3> -> void`
  - `Resolve-NextBootstrapAction -State <BootstrapStateV3> -Probe <RealProbeResult> -> BootstrapAction`
- Schema v3 stores only stage names, non-secret hashes, safe relative identifiers, timestamps, and restart intent. Real probes override stale stage markers.

### Readiness and acceptance layers

- Create `bootstrap/publisher-manifest.json` with exact publisher skill/bootstrap members and SHA-256 values.
- Create `acceptance/windows/acceptance-schema.json`, scenario scripts, and `ci/run-beginner-install-acceptance.ps1`.
- Acceptance evidence records scenario name, release identity, interaction count, redacted stage results, doctor round-trip status, archive status, A4 desktop-export status, exact-delete status, and sentinel preservation status.

---

### Task 0: Own every child process before running more aggregate tests

**Files:**
- Create: `ci/lib/OwnedProcess.psm1`
- Create: `tests/OwnedProcessContract.Tests.ps1`
- Modify: `ci/run-all-tests.ps1`
- Modify: `ci/run-python-tests.ps1`
- Modify: `ci/run-pester-tests.ps1`
- Modify: `tests/TestRunnerContract.Tests.ps1`
- Modify: `.github/workflows/windows-ci.yml`

**Interfaces:**
- Consumes: existing child runners and JSON summaries.
- Produces: the `OwnedRun` and `OwnedProcessResult` interfaces defined above, plus `artifacts/test-evidence.json` schema version 2.

- [ ] **Step 1: Add RED tests for owned process lifecycle.**

  Add synthetic success, nonzero exit, malformed JSON, parent timeout with a sleeping grandchild, runner exception, and evidence-write failure cases. The timeout case must assert that both the root child and its grandchild disappear while an unrelated sentinel PowerShell process remains alive.

  ```powershell
  It "closes only the run-owned process tree on timeout" {
      $sentinel = Start-Process pwsh -ArgumentList '-NoProfile','-Command','Start-Sleep 120' -PassThru -WindowStyle Hidden
      try {
          $result = Invoke-OwnedProcess -Run $run -Name 'timeout-tree' -FilePath 'pwsh' `
              -ArgumentList @('-NoProfile','-File',$spawnGrandchild) -WorkingDirectory $TestDrive -TimeoutSeconds 2
          $result.TimedOut | Should BeTrue
          (Get-Process -Id $sentinel.Id -ErrorAction SilentlyContinue) | Should Not BeNullOrEmpty
          Test-RunOwnedPidAlive -LedgerPath $run.LedgerPath | Should BeFalse
      } finally {
          Stop-Process -Id $sentinel.Id -Force -ErrorAction SilentlyContinue
      }
  }
  ```

- [ ] **Step 2: Run only the new focused contract and verify RED.**

  Run one PowerShell process, not five concurrent copies:

  ```powershell
  ./ci/run-pester-tests.ps1 -Path (Resolve-Path ./tests/OwnedProcessContract.Tests.ps1).Path -ExpectedSkipCount 0
  ```

  Expected: failures because `OwnedProcess.psm1` and Job Object ownership do not exist.

- [ ] **Step 3: Implement Windows Job Object ownership.**

  Use a small `Add-Type` C# interop wrapper for `CreateJobObject`, `SetInformationJobObject`, `AssignProcessToJobObject`, and `CloseHandle`. Configure `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, start each child suspended or assign it immediately before normal work, redirect stdout/stderr to run-owned files, and close the job in `finally`. Do not use global process-name matching.

- [ ] **Step 4: Route all aggregate children through `Invoke-OwnedProcess`.**

  `run-all-tests.ps1` must create one GUID run root, invoke Python and Pester as separate owned children, parse bounded output, write evidence before returning, and close the run in `finally`. Evidence must be produced for success, test failure, malformed child output, timeout, and runner exceptions.

- [ ] **Step 5: Prove the release-acquisition test is stable without unsafe repetition.**

  Execute `ReleaseAcquisitionContract.Tests.ps1` five times sequentially through the owned runner. Require 11 passed, 0 failed, 0 skipped each time. If cleanup still flakes, replace global download mocks with a test-injected downloader callback and repeat the five-run gate.

- [ ] **Step 6: Integrate aggregate evidence into Windows CI.**

  Add a CI job that invokes `run-all-tests.ps1`, validates schema-v2 evidence, and uploads only sanitized evidence. Keep the focused jobs for diagnostic separation. Package must depend on the aggregate evidence job as well.

- [ ] **Step 7: Run focused regression and commit.**

  Require `OwnedProcessContract` and `TestRunnerContract` to pass with zero skips, two aggregate runs to emit valid evidence, and both runs to report zero owned live processes.

  ```powershell
  git add ci/lib/OwnedProcess.psm1 ci/run-all-tests.ps1 ci/run-python-tests.ps1 ci/run-pester-tests.ps1 tests/OwnedProcessContract.Tests.ps1 tests/TestRunnerContract.Tests.ps1 .github/workflows/windows-ci.yml
  git commit -m "fix: own and recover all test child processes"
  ```

### Task 1: Install both Codex skills as one verified transaction

**Files:**
- Create: `bootstrap/lib/CodexSkills.psm1`
- Create: `bootstrap/install-codex-skills.ps1`
- Create: `bootstrap/codex-skills-manifest.json`
- Mirror under: `plugins/obsidian-manuscript-publisher/bootstrap/`
- Create: `tests/CodexSkillBootstrap.Tests.ps1`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-setup/SKILL.md`
- Modify: `tests/test_skill_sync.py`
- Modify: `ci/release-allowlist.txt`

**Interfaces:**
- Consumes: verified extracted release root from release acquisition.
- Produces: an exact pair of installed setup/publisher skills and machine-readable rollback evidence.

- [ ] **Step 1: Write RED tests.** Cover fresh install, exact reinstall, one missing source skill, extra source member, member hash mismatch, case collision, destination reparse point, existing skill backups, first-promotion failure, second-promotion failure, exact rollback, and final source/install parity.
- [ ] **Step 2: Verify RED** with only `CodexSkillBootstrap.Tests.ps1` and `tests.test_skill_sync`.
- [ ] **Step 3: Generate the exact skill manifest** from tracked allowlisted files and reject untracked or extra members.
- [ ] **Step 4: Implement staging, backup, promotion, and rollback.** Stage both skills under a GUID sibling directory; verify all members before changing the active roots; rename current roots to GUID backups; promote both staged roots; verify again; on any failure restore both previous roots exactly.
- [ ] **Step 5: Add beginner routing.** The setup skill must recognize the canonical first-install sentence and exact resume sentence without requiring the `codex plugin` command.
- [ ] **Step 6: Mirror, run focused regressions, scan secrets, and commit.**

  ```powershell
  git commit -m "feat: install Codex skills as one verified transaction"
  ```

### Task 2: Add verified no-WinGet prerequisites and schema-v3 resume

**Files:**
- Create/mirror: `bootstrap/lib/OfficialInstallers.psm1`
- Create/mirror: `bootstrap/lib/BootstrapState.psm1`
- Modify/mirror: `bootstrap/dependencies.lock.json`
- Modify/mirror: `bootstrap/install-windows.ps1`
- Modify/mirror: `bootstrap/lib/Environment.psm1`
- Modify/mirror: `bootstrap/lib/PythonRuntime.psm1`
- Create: `tests/OfficialInstallerContract.Tests.ps1`
- Create: `tests/BootstrapStateContract.Tests.ps1`
- Modify: `tests/InstallerContract.Tests.ps1`
- Modify: `tests/PythonRuntimeContract.Tests.ps1`
- Modify: `THIRD_PARTY_NOTICES.md`

**Interfaces:**
- Consumes: immutable dependency lock entries and the skill transaction from Task 1.
- Produces: verified Python/Obsidian prerequisites and `BootstrapStateV3` whose next action is selected by real probes.

- [ ] **Step 1: Add RED prerequisite tests.** Cover WinGet preference, no-WinGet fallback, non-HTTPS URL, SHA mismatch, signer mismatch, interrupted download, pre-existing partial, silent exit requiring restart, rediscovery after restart, and no global PATH mutation.
- [ ] **Step 2: Add RED state tests.** Cover every stage, atomic write, schema-v2 migration, truncated JSON, stale hashes, stale ready marker, restart after each prerequisite, empty-Vault numbered collision, idempotent rerun, and secret-bearing state rejection.
- [ ] **Step 3: Resolve official metadata during implementation.** Use only official Python and Obsidian release sources; record exact x64 Windows installer URL, release version, SHA-256, expected Authenticode subject, and silent arguments in the dependency lock. Commit no installer binary.
- [ ] **Step 4: Implement verified `.partial` acquisition** through Task 0's owned process runner. Verify URL, bytes, SHA-256, signer, and exit code before accepting installation; discard owned partials on every failure.
- [ ] **Step 5: Implement schema-v3 atomic state and real-probe resume.** Stage markers are hints. A missing executable, mismatched skill hash, missing Vault marker, or failed doctor probe must move the state backward to the earliest safe action.
- [ ] **Step 6: Run focused contracts, exact root/package parity, privacy scan, and commit.**

  ```powershell
  git commit -m "feat: verify prerequisites and resume setup safely"
  ```

### Task 3: Make doctor the only readiness authority

**Files:**
- Create/mirror: `bootstrap/publisher-manifest.json`
- Modify/mirror: `bootstrap/doctor.ps1`
- Modify/mirror: `bootstrap/install-windows.ps1`
- Modify/mirror: `bootstrap/lib/LocalRest.psm1`
- Modify/mirror: `bootstrap/lib/Vault.psm1`
- Modify/mirror: `bootstrap/lib/PublicationLibrary.psm1`
- Create: `tests/BeginnerDoctorContract.Tests.ps1`
- Modify: Local REST, archive, publication, desktop export, and deletion regressions.

**Interfaces:**
- Consumes: schema-v3 state, verified publisher manifest, and loopback HTTPS configuration.
- Produces: `ready` only after exact publisher verification and a byte-identical Local REST create/read/delete round trip.

- [ ] **Step 1: Add RED tests** for missing/partial configuration, delayed Obsidian startup, invalid port, non-loopback host, HTTP, redirect, missing certificate, secret redaction, create/read byte mismatch, delete failure, publisher manifest mismatch, unsafe publication root, and filesystem fallback attempts.
- [ ] **Step 2: Generate the publisher manifest** from the release allowlist and reject missing, changed, or extra publisher members.
- [ ] **Step 3: Implement bounded doctor retry.** Before doctor succeeds, state is `awaiting_obsidian` or `doctor_required`; installer code cannot emit `ready`.
- [ ] **Step 4: Perform the real round trip.** Write a random non-secret probe note through HTTPS, read exact bytes, delete the exact note, verify absence, and scrub temporary curl config in `finally`.
- [ ] **Step 5: Run existing archive/publish/export/delete regressions** to prove no change to current manuscript behavior.
- [ ] **Step 6: Mirror, verify, and commit.**

  ```powershell
  git commit -m "feat: make doctor authoritative for readiness"
  ```

### Task 4: Make the beginner promise testable in docs, acceptance, CI, and packages

**Files:**
- Modify: `README.md`
- Modify: `INSTALL_PROMPT.md`
- Modify: `docs/INSTALL_GUIDE.md`
- Modify: `docs/TROUBLESHOOTING.md`
- Modify: `docs/RELEASE.md`
- Create: `acceptance/windows/acceptance-schema.json`
- Create: `acceptance/windows/Invoke-BeginnerScenario.ps1`
- Create: `acceptance/windows/scenarios.json`
- Create: `ci/run-beginner-install-acceptance.ps1`
- Create/modify: documentation, acceptance, CI, release, privacy, and package contract tests.

**Interfaces:**
- Consumes: doctor-ready setup and all product pipelines.
- Produces: sanitized acceptance evidence and a release package that cannot be built unless every prerequisite gate passes.

- [ ] **Step 1: Add RED documentation tests.** Require one copy-ready install request, one resume sentence, one consolidated consent, no shell/API-key/certificate handling by the beginner, three first-use requests, valid links, `requirements.lock.txt`, and no claim that `v0.5.2` is public before release.
- [ ] **Step 2: Add RED acceptance-schema tests.** Reject secrets, private absolute paths, undeclared interactions, release mismatch, missing doctor proof, missing archive/A4 export/exact delete, and deleted sentinel notes.
- [ ] **Step 3: Implement isolated scenario execution.** All scenario roots live under a GUID temp root. Never use the user's existing Vault, skill roots, or desktop publication folder. Emit evidence even on interruption.
- [ ] **Step 4: Cover scenarios.** Include Codex-only, no-WinGet, required restart/resume, path collision, interrupted download, tampered release, delayed REST, and previous-skill upgrade/rollback.
- [ ] **Step 5: Correct documentation contracts.** Change premature public-version language to “latest verified stable release” until release; replace `requirements.txt` recovery wording with `requirements.lock.txt`; document expected Python skips as exactly four.
- [ ] **Step 6: Gate the package job.** The package job must depend on focused contracts, aggregate evidence, privacy/secret scan, source/package parity, and acceptance-schema validation.
- [ ] **Step 7: Build twice and compare.** Require identical ZIP member names and each member's SHA-256, then verify both archives in distinct fresh roots.
- [ ] **Step 8: Commit.**

  ```powershell
  git commit -m "ci: verify the complete beginner installation promise"
  ```

### Task 5: Review, promote locally, and prove clean-Windows behavior

**Files:**
- Modify only when a reproduced defect requires a RED test and focused fix.
- Write sanitized evidence under `artifacts/acceptance/`; release allowlists must exclude raw machine/user data.

**Interfaces:**
- Consumes: release candidate archive, checksums, manifests, and acceptance runner.
- Produces: reviewed local installation backup, exact installed/source parity, and disposable-Windows evidence.

- [ ] **Step 1: Run nine time-bounded read-only reviews.** Review release trust, process ownership, skill rollback, official installers, resume state, Local REST, path/deletion safety, reproducibility/beginner UX, and adversarial completion claims. Each reviewer returns classification, P0–P3, exact file/line, reproduction, and test recommendation.
- [ ] **Step 2: Independently reproduce blockers.** Every accepted P0/P1 and installation-affecting P2 receives a new failing test before a fix. Rejected findings are recorded with evidence.
- [ ] **Step 3: Run the complete local verification once through the owned runner.** Require Python failures/errors 0 with exactly four documented skips; Pester failures/skips/pending/inconclusive 0; aggregate schema-v2 success; zero owned live processes; exact root/package parity; clean secret/privacy scans.
- [ ] **Step 4: Back up both installed skills.** Use a new timestamped backup next to the existing backup. Promote the verified pair through Task 1's transaction, check exact parity, and run fake-release/fake-REST smoke. Restore both immediately on any failure.
- [ ] **Step 5: Run disposable Windows acceptance.** Windows Sandbox, VM, or fresh local account must start with Codex only. The primary flow permits initial request, consolidated consent, and requested restart continuation only.
- [ ] **Step 6: Stop safely if disposable Windows is unavailable.** Report a verified local release candidate and the exact missing gate. Do not merge, tag, release, or call the work publicly complete.

### Task 6: Publish an immutable GitHub release only after explicit authorization

**Files:**
- Update release version/notes only after all earlier gates pass.
- Do not modify an existing tag or release asset.

**Interfaces:**
- Consumes: clean reviewed merge candidate and disposable-Windows evidence.
- Produces: merged PR, annotated immutable tag, public assets and checksums, and public fresh-install evidence.

- [ ] **Step 1: Confirm authorization and repository state.** The active user request must include `GitHub 배포까지 승인`; tracked worktree must be clean; remote must not contain a conflicting tag; no secret or user-data diff may exist.
- [ ] **Step 2: Push without force and update Draft PR #6.** Wait for all required checks. A failed, cancelled, or unexpectedly skipped check blocks merge.
- [ ] **Step 3: Merge the reviewed head.** Record the merge commit and rebuild assets from that exact commit.
- [ ] **Step 4: Create annotated `v0.5.2` once.** Publish ZIP, release manifest, `SHA256SUMS`, publisher manifest, notes, and sanitized acceptance evidence.
- [ ] **Step 5: Redownload every public asset.** In a new root, verify tag → merge commit → manifest → archive → member hashes and run release verification.
- [ ] **Step 6: Run the README flow from a fresh Windows account.** Verify doctor, conversation archive, A4 desktop export, and exact current-conversation deletion while sentinel files remain.
- [ ] **Step 7: Mark latest only after public reinstall succeeds.** If the reinstall fails, keep the release non-latest, publish no success claim, diagnose with a new failing test, and issue a new version rather than moving the tag.

## Final Verification Commands

Run through the Task 0 owned runner, not as unmanaged duplicate processes:

```powershell
$python = 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $python -m unittest discover -s tests -p 'test_*.py'
./ci/run-pester-tests.ps1 -Path (Get-ChildItem ./tests/*.Tests.ps1 | ForEach-Object FullName) -ExpectedSkipCount 0
./ci/run-all-tests.ps1 -PythonPath $python -ExpectedPythonSkipCount 4 -ExpectedPesterSkipCount 0
```

The final report must state exact pass/fail/skip counts, evidence paths and hashes, owned-process count, source/package/installed parity, backup locations, security/license results, disposable-Windows status, GitHub operations actually performed, and remaining P0–P3. Unverified facts must be labelled unverified.

## Self-Review Result

- Spec coverage: all known blockers map to Tasks 0–6.
- Ordering: aggregate tests cannot run before owned process control; public release cannot run before disposable-Windows evidence.
- Existing functionality: archive, delete, book A4, adaptive blog, custom manuscript, Local REST publication, and desktop export are regression gates rather than redesign targets.
- Safety: no broad process termination, Vault filesystem fallback, moving tag, force push, or premature release claim is permitted.
- Placeholders: the plan contains no deferred implementation markers; unresolved vendor metadata is an explicit verified acquisition step because its exact value must come from the official release selected during execution.
