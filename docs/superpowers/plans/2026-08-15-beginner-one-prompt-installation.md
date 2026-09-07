# Beginner One-Prompt Installation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a Windows beginner who has only Codex installed paste one request, approve the required installation, resume once after a restart if necessary, and reach a doctor-verified, immediately usable `obsidian-manuscript-publisher` environment without entering shell commands or handling secrets.

**Architecture:** A verified GitHub release-acquisition layer installs the two Codex skills atomically, then a resumable Windows setup state machine installs or discovers Python and Obsidian, creates a dedicated Vault, enables pinned Local REST, and runs doctor. Automated Windows CI proves deterministic contracts and release packaging; a separate clean-Windows acceptance gate proves the interactive Codex/Obsidian flow before an immutable public release is marked latest.

**Tech Stack:** Windows PowerShell 5.1, Python 3.12, Pester 3-compatible tests, Python `unittest`, GitHub Actions, SHA-256, Authenticode, Obsidian Local REST API 5.0.2, Codex skills/plugins, GitHub CLI for maintainer release operations.

## Global Constraints

- Target Windows 10/11 x64 with Codex already installed and authenticated.
- Do not assume WinGet, Python, Git, GitHub CLI, Obsidian, curl on `PATH`, or a working Codex plugin CLI.
- The beginner enters no shell command and never copies an API key, certificate, JSON value, or internal path.
- Installation requires one consolidated consent for Obsidian, the dedicated Vault, and pinned Local REST; do not bypass consent.
- Install only a stable immutable GitHub release from `ARTHONG1/codex-obsidian-manuscript-starter`; never install a branch head.
- Never execute a downloaded script before release archive, manifest, checksum, ZIP-path, and allowlist validation.
- Never use `irm | iex` or an equivalent remote-script pipeline.
- Use only `https://127.0.0.1:<validated-port>` for Local REST; never enable plaintext HTTP or external exposure.
- Never print, log, publish, or commit API keys, certificate bodies, tokens, Vault content, or manuscript content.
- Preserve existing Vaults, files, plugin settings, and skill installations; use exact-path backup and rollback.
- Do not mark installation complete until doctor passes Local REST create/read/delete and publisher-manifest verification.
- Do not merge, tag, or release while any required CI, privacy, clean-Windows, or public-redownload gate fails.
- Preserve all existing archive, delete, `book_a4`, `adaptive_blog`, `custom_manuscript`, Local REST, immutable-version, and Desktop publication behavior.

---

## File Responsibility Map

- `bootstrap/release-acquisition.psm1`: resolve, download, and verify immutable public release assets.
- `bootstrap/install-codex-skills.ps1`: atomically promote the setup and publisher skills from a verified extracted release.
- `bootstrap/lib/OfficialInstallers.psm1`: discover WinGet or safely download and execute pinned official Python/Obsidian installers.
- `bootstrap/lib/BootstrapState.psm1`: schema-v3 resumable stage persistence and real-state probes.
- `bootstrap/install-windows.ps1`: coordinate consent-approved environment installation; no test-only switches.
- `bootstrap/doctor.ps1`: Local REST round trip, publisher identity, and publication-library readiness.
- `ci/run-installer-scenario.ps1`: test-only installer scenario harness; never shipped as the production installer entry point.
- `ci/build-release.ps1`: create allowlisted archive, release manifest, and checksums.
- `ci/verify-release.ps1`: validate release assets before extraction and perform clean-root verification.
- `acceptance/windows/`: sanitized clean-Windows execution guide, evidence schema, and validator.
- `.github/workflows/windows-ci.yml`: reproducible contract, installer, package, and artifact gates.
- `README.md`, `INSTALL_PROMPT.md`, `docs/INSTALL_GUIDE.md`, `docs/TROUBLESHOOTING.md`, `docs/RELEASE.md`: beginner-first and maintainer release documentation.

---

### Task 1: Repair the Windows CI foundation

**Files:**
- Modify: `.github/workflows/windows-ci.yml`
- Create: `ci/run-installer-scenario.ps1`
- Modify: `tests/test_ci_contract.py`
- Create: `tests/InstallerScenarioContract.Tests.ps1`
- Modify: `ci/action-lock.json`

**Interfaces:**
- Consumes: pinned actions from `ci/action-lock.json`, Python requirements from `requirements-dev.txt`, production installer from `bootstrap/install-windows.ps1`.
- Produces: `ci/run-installer-scenario.ps1 -Scenario <name> -TestRoot <path>` returning process exit 0 only when the named isolated scenario passes.

- [ ] **Step 1: Add failing CI contract tests**

Add assertions that the workflow uses `actions/setup-python`, installs `requirements-dev.txt`, passes `(Get-Command python).Source`, invokes `ci/run-installer-scenario.ps1`, and never passes `-Scenario` to `bootstrap/install-windows.ps1`.

```python
def test_workflow_installs_dependencies_and_uses_test_harness(self):
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "python -m pip install -r requirements-dev.txt" in workflow
    assert "-PythonPath (Get-Command python).Source" in workflow
    assert ".\\ci\\run-installer-scenario.ps1" in workflow
    assert "install-windows.ps1 -RuntimeRoot" not in workflow or "-Scenario" not in workflow
```

- [ ] **Step 2: Run RED tests**

Run:

```powershell
python -m unittest tests.test_ci_contract -v
```

Expected: failure for the stale `3.12.0` path, missing dependency installation, and unsupported production `-Scenario` argument.

- [ ] **Step 3: Implement the dedicated scenario harness**

Create a Pester-compatible harness with the exact public parameter contract:

```powershell
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('python311_selected','python313_selected','python_absent','python312_ready','restart_resume','venv_reuse')]
    [string]$Scenario,
    [Parameter(Mandatory=$true)][string]$TestRoot
)
```

The script must construct scenario-specific fake discovery/process runners, invoke production modules without modifying the host, write only below `$TestRoot`, and fail on an unexpected status.

- [ ] **Step 4: Repair the workflow**

Use immutable action SHAs, `setup-python` in every Python-dependent job, then run:

```powershell
python -m pip install --disable-pip-version-check -r requirements-dev.txt
```

Use `(Get-Command python).Source` in every runner invocation. Replace production installer matrix calls with `ci/run-installer-scenario.ps1`.

- [ ] **Step 5: Verify Task 1**

Run:

```powershell
python -m unittest tests.test_ci_contract -v
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\InstallerScenarioContract.Tests.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\TestRunnerContract.Tests.ps1
```

Expected: all pass, zero skips.

- [ ] **Step 6: Commit Task 1**

```powershell
git add .github/workflows/windows-ci.yml ci/run-installer-scenario.ps1 ci/action-lock.json tests/test_ci_contract.py tests/InstallerScenarioContract.Tests.ps1
git commit -m "ci: repair Windows beginner installation gates"
```

---

### Task 2: Create the immutable release manifest and acquisition verifier

**Files:**
- Create: `bootstrap/release-acquisition.psm1`
- Modify: `ci/build-release.ps1`
- Modify: `ci/verify-release.ps1`
- Modify: `ci/release-allowlist.txt`
- Create: `tests/ReleaseAcquisitionContract.Tests.ps1`
- Modify: `tests/test_release_package.py`

**Interfaces:**
- Produces: `Resolve-StableRelease -Repository <owner/name>` returning `Repository`, `Version`, `Tag`, `Commit`, `ArchiveUrl`, `ManifestUrl`, and `ChecksumsUrl`.
- Produces: `Get-VerifiedRelease -Release <object> -DownloadRoot <path>` returning an extracted immutable `ReleaseRoot` only after complete validation.
- Produces release asset `release-manifest.json` with `schemaVersion`, `repository`, `version`, `tag`, `commit`, `archive`, `archiveSha256`, and sorted `files` entries.

- [ ] **Step 1: Add failing release-acquisition tests**

Test stable-release selection, prerelease rejection, owner/repository mismatch, tag/manifest mismatch, checksum mismatch, branch-archive rejection, unsafe ZIP paths, duplicate names, case collisions, and an unexpected executable.

```powershell
It 'rejects a manifest whose repository differs from the requested repository' {
    { Test-ReleaseManifest -Manifest $manifest -ExpectedRepository 'ARTHONG1/codex-obsidian-manuscript-starter' } |
        Should Throw '*release_repository_mismatch*'
}
```

- [ ] **Step 2: Run RED tests**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\ReleaseAcquisitionContract.Tests.ps1
python -m unittest tests.test_release_package -v
```

Expected: failure because release-manifest generation and acquisition functions do not exist.

- [ ] **Step 3: Implement release-manifest generation**

After building the ZIP, calculate its SHA-256 and emit canonical UTF-8 JSON. `SHA256SUMS` contains one line for the ZIP and one for `release-manifest.json`, sorted by basename. The manifest must not include its own digest.

- [ ] **Step 4: Implement safe acquisition**

Use `System.Net.Http.HttpClient` with redirects disabled for identity-sensitive metadata and bounded redirects only to GitHub-owned release-asset hosts for binary assets. Download to installer-owned `.partial` files, verify size and digest, rename atomically, inspect every ZIP member, then extract into a new owned directory.

- [ ] **Step 5: Verify Task 2**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\ReleaseAcquisitionContract.Tests.ps1
python -m unittest tests.test_release_package tests.test_release_privacy_contract -v
```

Expected: all pass, no secret or path disclosure.

- [ ] **Step 6: Commit Task 2**

```powershell
git add bootstrap/release-acquisition.psm1 ci/build-release.ps1 ci/verify-release.ps1 ci/release-allowlist.txt tests/ReleaseAcquisitionContract.Tests.ps1 tests/test_release_package.py
git commit -m "feat: verify immutable release acquisition"
```

---

### Task 3: Add atomic Codex skill bootstrap and rollback

**Files:**
- Create: `bootstrap/install-codex-skills.ps1`
- Create: `bootstrap/lib/CodexSkills.psm1`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-setup/SKILL.md`
- Create: `tests/CodexSkillBootstrap.Tests.ps1`
- Modify: `tests/test_skill_sync.py`
- Modify: `ci/release-allowlist.txt`

**Interfaces:**
- Produces: `Install-VerifiedCodexSkills -ReleaseRoot <path> -CodexSkillsRoot <path> -ReleaseManifest <object>`.
- Returns: `Status`, `Version`, `InstalledSkills`, `BackupRoots`, `RestartRequired` without secret values.

- [ ] **Step 1: Add failing atomic-promotion tests**

Cover fresh install, exact idempotent reinstall, existing-version backup, promotion failure rollback, manifest mismatch, destination reparse point, case-colliding files, and publisher/setup skill pair completeness.

- [ ] **Step 2: Run RED tests**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\CodexSkillBootstrap.Tests.ps1
```

Expected: failure because `CodexSkills.psm1` and the installer entry point do not exist.

- [ ] **Step 3: Implement exact allowlisted promotion**

Copy both skill trees to sibling staging directories, verify each staged hash against `release-manifest.json`, rename any existing exact destination to a GUID backup, promote both staged trees, compare source/destination manifests, then delete staging only after success. If either skill fails, restore both previous destinations.

- [ ] **Step 4: Add setup-skill continuation contract**

The setup skill must detect `skills_installed` state, explain when a Codex restart is required, and use exactly this resume request:

```text
중단된 Codex Obsidian Manuscript Starter 설치를 이어서 진행해줘.
```

- [ ] **Step 5: Verify Task 3**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\CodexSkillBootstrap.Tests.ps1
python -m unittest tests.test_skill_sync tests.test_documentation_contract -v
```

- [ ] **Step 6: Commit Task 3**

```powershell
git add bootstrap/install-codex-skills.ps1 bootstrap/lib/CodexSkills.psm1 plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-setup/SKILL.md tests/CodexSkillBootstrap.Tests.ps1 tests/test_skill_sync.py ci/release-allowlist.txt
git commit -m "feat: bootstrap Codex skills atomically"
```

---

### Task 4: Add pinned no-WinGet official installer fallback

**Files:**
- Create: `bootstrap/lib/OfficialInstallers.psm1`
- Modify: `bootstrap/lib/PythonRuntime.psm1`
- Modify: `bootstrap/lib/Environment.psm1`
- Modify: `bootstrap/install-windows.ps1`
- Modify: `dependencies.lock.json`
- Mirror: `bootstrap/dependencies.lock.json`
- Mirror: `plugins/obsidian-manuscript-publisher/bootstrap/**`
- Create: `tests/OfficialInstallerContract.Tests.ps1`
- Modify: `tests/PythonRuntimeContract.Tests.ps1`
- Modify: `tests/InstallerContract.Tests.ps1`
- Modify: `THIRD_PARTY_NOTICES.md`

**Interfaces:**
- Produces: `Install-PinnedOfficialApplication -Application Python|Obsidian -DependencyLock <object> -DownloadRoot <path> -ProcessRunner <scriptblock>`.
- Returns: `Status`, `Version`, `RestartRequired`, `Executable`; never returns installer bytes or secrets.

- [ ] **Step 1: Add failing official-installer tests**

Test WinGet preference, no-WinGet fallback, HTTPS-only URLs, pinned SHA-256, expected Authenticode signer allowlist, silent per-user arguments, download interruption, signature mismatch, digest mismatch, installer failure, and post-install rediscovery.

- [ ] **Step 2: Run RED tests**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\OfficialInstallerContract.Tests.ps1
```

- [ ] **Step 3: Resolve and pin current official installers**

From official Python and Obsidian release sources, download the selected x64 installers in a maintainer-only temporary directory. Record exact version, HTTPS URL, SHA-256, Authenticode subject/issuer, product name, and documented quiet per-user arguments in all three lock copies. Verify lock-copy byte identity and update third-party notices without redistributing installers.

- [ ] **Step 4: Implement safe fallback execution**

Download to an owned temporary path, verify digest and Authenticode before execution, run with argument arrays rather than command strings, capture exit code, rediscover the installed executable, and persist restart-required state. Never add arbitrary locations to global `PATH`.

- [ ] **Step 5: Verify Task 4**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\OfficialInstallerContract.Tests.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\PythonRuntimeContract.Tests.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\InstallerContract.Tests.ps1
python -m unittest tests.test_dependency_contract -v
```

- [ ] **Step 6: Commit Task 4**

```powershell
git add bootstrap plugins/obsidian-manuscript-publisher/bootstrap dependencies.lock.json tests/OfficialInstallerContract.Tests.ps1 tests/PythonRuntimeContract.Tests.ps1 tests/InstallerContract.Tests.ps1 THIRD_PARTY_NOTICES.md
git commit -m "feat: install pinned official prerequisites without winget"
```

---

### Task 5: Implement schema-v3 resumable beginner setup

**Files:**
- Create: `bootstrap/lib/BootstrapState.psm1`
- Modify: `bootstrap/lib/Environment.psm1`
- Modify: `bootstrap/install-windows.ps1`
- Mirror: `plugins/obsidian-manuscript-publisher/bootstrap/**`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-setup/SKILL.md`
- Create: `tests/BootstrapStateContract.Tests.ps1`
- Modify: `tests/InstallerContract.Tests.ps1`

**Interfaces:**
- Produces: `Get-BootstrapState`, `Save-BootstrapState`, `Test-BootstrapStage`, and `Get-NextBootstrapStage`.
- State schema 3 contains `schemaVersion`, `release`, `commit`, `lastCompletedStage`, `vaultPath`, `runtimeRoot`, `publicationRoot`, `installedVersions`, and hashes only.

- [ ] **Step 1: Add failing state-machine tests**

Cover all exact stages from `preflight` through `ready`, atomic JSON writes, truncated-state recovery, schema-v2 migration, restart after each installation stage, stale marker with failed real probe, no secret keys, and idempotent rerun.

- [ ] **Step 2: Run RED tests**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\BootstrapStateContract.Tests.ps1
```

- [ ] **Step 3: Implement schema-v3 state and probes**

Use the exact stage order from the design. Every transition requires a real probe. Write JSON to an owned sibling temporary file and atomically replace `install-state.json`. Reject unknown stages and unsupported schemas.

- [ ] **Step 4: Consolidate consent and default paths**

The setup skill asks one consent question. After approval it calls the installer with an internal consent flag; the production script refuses app/plugin mutation without it. Resolve Windows Documents and Desktop through known-folder APIs. Select a new numbered empty Vault when the default collides; never remove the colliding folder.

- [ ] **Step 5: Verify Task 5**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\BootstrapStateContract.Tests.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\InstallerContract.Tests.ps1
```

- [ ] **Step 6: Commit Task 5**

```powershell
git add bootstrap plugins/obsidian-manuscript-publisher/bootstrap plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-setup/SKILL.md tests/BootstrapStateContract.Tests.ps1 tests/InstallerContract.Tests.ps1
git commit -m "feat: resume beginner installation safely"
```

---

### Task 6: Complete Obsidian launch, Local REST readiness, and publisher doctor

**Files:**
- Modify: `bootstrap/lib/Vault.psm1`
- Modify: `bootstrap/lib/LocalRest.psm1`
- Modify: `bootstrap/lib/PublicationLibrary.psm1`
- Modify: `bootstrap/doctor.ps1`
- Modify: `bootstrap/install-windows.ps1`
- Mirror: `plugins/obsidian-manuscript-publisher/bootstrap/**`
- Create: `bootstrap/publisher-manifest.json`
- Create: `tests/BeginnerDoctorContract.Tests.ps1`
- Modify: `tests/InstallerContract.Tests.ps1`
- Modify: `tests/test_local_rest_security.py`

**Interfaces:**
- Produces: doctor JSON fields `status`, `releaseVersion`, `vaultStatus`, `restStatus`, `roundTripStatus`, `publisherStatus`, and `publicationLibraryStatus`.
- `status` equals `ready` only when all five subordinate statuses are `ready`.

- [ ] **Step 1: Add failing doctor tests**

Cover validated Obsidian launch with the dedicated Vault, delayed/partial `data.json`, explicit port bounds, HTTPS-only connection, redirect rejection, certificate/API-key non-output, create/read/delete byte equality, publisher-manifest mismatch, Desktop known-folder resolution, and no direct Vault-write fallback.

- [ ] **Step 2: Run RED tests**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\BeginnerDoctorContract.Tests.ps1
python -m unittest tests.test_local_rest_security -v
```

- [ ] **Step 3: Implement publisher manifest and doctor verification**

Generate a sorted publisher file manifest during release build. Doctor hashes the installed publisher skill, compares exact file membership and hashes, performs the `_system` Local REST round trip, and updates `doctor_verified`, `publisher_verified`, then `ready` only after success.

- [ ] **Step 4: Normalize completion output**

The setup skill reports only release version, Vault path, doctor status, and these first-use requests:

```text
이 프로젝트를 원고 프로젝트로 등록해줘.
이 대화 전체를 옵시디언 원고 재료로 저장해줘.
이 대화 재료로 출판 원고를 만들어줘.
```

- [ ] **Step 5: Verify Task 6**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\BeginnerDoctorContract.Tests.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\InstallerContract.Tests.ps1
python -m unittest tests.test_local_rest_security tests.test_archive_conversation tests.test_publish_manuscript_version -v
```

- [ ] **Step 6: Commit Task 6**

```powershell
git add bootstrap plugins/obsidian-manuscript-publisher/bootstrap plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-setup/SKILL.md tests/BeginnerDoctorContract.Tests.ps1 tests/InstallerContract.Tests.ps1 tests/test_local_rest_security.py
git commit -m "feat: verify Obsidian and publisher readiness"
```

---

### Task 7: Rebuild the beginner documentation contract

**Files:**
- Modify: `README.md`
- Modify: `INSTALL_PROMPT.md`
- Modify: `docs/INSTALL_GUIDE.md`
- Modify: `docs/TROUBLESHOOTING.md`
- Modify: `docs/RELEASE.md`
- Modify: `docs/USAGE_GUIDE.md`
- Modify: `tests/test_documentation_contract.py`
- Modify: `tests/test_obsidian_manuscript_workspace.py`

**Interfaces:**
- Produces one canonical Korean installation request shared verbatim by README and `INSTALL_PROMPT.md`.
- Produces one canonical resume request and three first-use requests.

- [ ] **Step 1: Add failing beginner-documentation tests**

Assert beginner-first order, one installation request, no “3분” promise, no required shell command, no API-key/certificate instructions, no nonexistent tag, local-link validity, consolidated consent wording, resume wording, and correct first-use requests.

- [ ] **Step 2: Run RED tests**

```powershell
python -m unittest tests.test_documentation_contract tests.test_obsidian_manuscript_workspace -v
```

- [ ] **Step 3: Rewrite the beginner surface**

Place product summary, copyable request, approval explanation, automatic actions, resume request, first-use requests, and compact troubleshooting above developer material. Move CLI and maintainer commands below an “고급 사용자·개발자” heading. Reference `v0.5.2` only after release candidate assets and manifest exist in the branch; the public README changes become authoritative at release merge.

- [ ] **Step 4: Verify Task 7**

```powershell
python -m unittest tests.test_documentation_contract tests.test_obsidian_manuscript_workspace -v
```

- [ ] **Step 5: Commit Task 7**

```powershell
git add README.md INSTALL_PROMPT.md docs tests/test_documentation_contract.py tests/test_obsidian_manuscript_workspace.py
git commit -m "docs: make one-prompt installation beginner first"
```

---

### Task 8: Add automated beginner-install acceptance harnesses

**Files:**
- Create: `acceptance/windows/acceptance-schema.json`
- Create: `acceptance/windows/validate-evidence.py`
- Create: `acceptance/windows/README.md`
- Create: `ci/run-beginner-install-acceptance.ps1`
- Create: `tests/BeginnerAcceptanceContract.Tests.ps1`
- Create: `tests/test_acceptance_evidence.py`
- Modify: `ci/release-allowlist.txt`

**Interfaces:**
- Produces sanitized `beginner-install-evidence.json` with scenario, Windows version, start-state flags, release version/commit, interaction count, stage results, doctor result, smoke-test result, cleanup result, and no personal absolute paths.

- [ ] **Step 1: Add failing evidence and harness tests**

Reject evidence with extra terminal interactions, secrets, absolute user paths, missing doctor round trip, missing conversation smoke test, failed deletion isolation, or mismatched release commit.

- [ ] **Step 2: Run RED tests**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\BeginnerAcceptanceContract.Tests.ps1
python -m unittest tests.test_acceptance_evidence -v
```

- [ ] **Step 3: Implement the test harness**

The automated harness uses only temporary roots and fake installers/REST for destructive branches. The real clean-Windows guide requires the tester to start with Codex only and records only the initial paste, consolidated consent, and restart continuation as permitted interactions.

- [ ] **Step 4: Implement product smoke verification**

The acceptance sequence registers an isolated test project, archives one test conversation, reads the raw archive/material card via Local REST, publishes a minimal A4 bundle, verifies Desktop output, deletes the exact conversation bundle, and proves a neighboring sentinel note remains.

- [ ] **Step 5: Verify Task 8**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\BeginnerAcceptanceContract.Tests.ps1
python -m unittest tests.test_acceptance_evidence tests.test_archive_conversation tests.test_delete_conversation_bundle tests.test_desktop_publication_export -v
```

- [ ] **Step 6: Commit Task 8**

```powershell
git add acceptance ci/run-beginner-install-acceptance.ps1 ci/release-allowlist.txt tests/BeginnerAcceptanceContract.Tests.ps1 tests/test_acceptance_evidence.py
git commit -m "test: gate release on beginner installation evidence"
```

---

### Task 9: Integrate full CI, package, privacy, and parity gates

**Files:**
- Modify: `.github/workflows/windows-ci.yml`
- Modify: `ci/run-all-tests.ps1`
- Modify: `ci/build-release.ps1`
- Modify: `ci/verify-release.ps1`
- Modify: `tests/TestRunnerContract.Tests.ps1`
- Modify: `tests/SecretScan.Tests.ps1`
- Modify: `tests/test_release_privacy_contract.py`
- Modify: `tests/test_release_package.py`

**Interfaces:**
- CI package job consumes only successful contract, installer, Python, Pester, privacy, and acceptance-contract jobs.
- Produces release archive, release manifest, `SHA256SUMS`, publisher manifest, and test evidence artifacts.

- [ ] **Step 1: Add failing aggregate-gate tests**

Assert all required jobs are dependencies of package, all actions are immutable SHAs, all Python jobs install dependencies, source/packaged bootstrap trees are byte-identical, privacy scans inspect ZIP members before extraction, and acceptance evidence is validated before release artifact creation.

- [ ] **Step 2: Run RED tests**

```powershell
python -m unittest tests.test_ci_contract tests.test_release_package tests.test_release_privacy_contract -v
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\TestRunnerContract.Tests.ps1
```

- [ ] **Step 3: Integrate the gates**

Keep all generated state under runner temporary directories. Package only tracked allowlisted files. Upload evidence with `if: always()` but never upload temporary Vaults, user paths, installer binaries, API data, or generated manuscripts.

- [ ] **Step 4: Run the complete local suite**

```powershell
$python = 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
.\ci\run-all-tests.ps1 -PythonPath $python -ExpectedPythonSkipCount 4
```

Expected: Python failures 0, errors 0, exactly 4 documented environment skips; Pester failures 0, skips 0.

- [ ] **Step 5: Build and verify two identical release candidates**

Build twice into separate temporary roots. Compare ZIP member names and every member SHA-256, then run `ci/verify-release.ps1` against each new extraction root.

- [ ] **Step 6: Commit Task 9**

```powershell
git add .github/workflows/windows-ci.yml ci tests/TestRunnerContract.Tests.ps1 tests/SecretScan.Tests.ps1 tests/test_ci_contract.py tests/test_release_package.py tests/test_release_privacy_contract.py
git commit -m "ci: enforce reproducible beginner release gates"
```

---

### Task 10: Execute independent security and quality review

**Files:**
- Modify only files required to resolve verified findings.
- Record: `.planning/beginner-one-prompt-implementation/review-report.md`

**Interfaces:**
- Review findings use `verified_defect`, `credible_risk`, `documentation_gap`, `improvement`, or `not_an_issue`, with P0-P3 severity, exact file/line, reproduction, and required test.

- [ ] **Step 1: Dispatch independent read-only audits**

Audit release acquisition, skill promotion/rollback, official installer trust, state migration/resume, Local REST secrecy/TLS, path/reparse handling, CI/package reproducibility, documentation UX, and adversarial overall design.

- [ ] **Step 2: Deduplicate and independently reproduce P0/P1/P2 findings**

Do not change code based only on a speculative finding. Reproduce each accepted finding with a failing test.

- [ ] **Step 3: Fix accepted findings with TDD**

For every accepted issue: add the narrow failing test, confirm RED, implement the minimum correction, rerun focused and full regression suites, and commit a focused change.

- [ ] **Step 4: Re-review the final diff**

Completion requires no unresolved P0, P1, or installation-affecting P2. Document any non-blocking P3 without weakening tests or release criteria.

- [ ] **Step 5: Commit review remediations**

Use one focused commit per independent remediation; do not squash evidence-producing test commits before review completion.

---

### Task 11: Promote and smoke-test the installed local skills

**Files:**
- Use: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/verify_skill_sync.py`
- Backup only: resolved current Codex skill destinations

**Interfaces:**
- Promotion returns `status: promoted`, exact source/destination file counts, zero missing/extra/changed files, and a backup path.

- [ ] **Step 1: Compare source and installed candidates**

Run compare mode for setup and publisher skills. Record exact differences without mutation.

- [ ] **Step 2: Back up and promote verified skill trees**

Promote only after Tasks 1-10 pass. Use timestamp/GUID backups and exact manifest comparison. If post-promotion smoke fails, restore both backups.

- [ ] **Step 3: Run installed-skill smoke in temporary roots**

Use fake release/installer/REST endpoints and temporary Vault/runtime/publication roots. Verify setup routing, publisher routing, doctor output, and no writes outside the test roots.

- [ ] **Step 4: Re-run exact sync**

Expected: source and installed setup/publisher skills have zero missing, extra, or changed files.

---

### Task 12: Complete public GitHub release and public-install retest

**Files:**
- Modify: plugin/version metadata, `CITATION.cff`, README/install prompt release references, release notes, and dependency locks only when required by the final release commit.
- Create release assets from verified CI output only.

**Interfaces:**
- Produces immutable annotated tag `v0.5.2`, GitHub release assets, and a public-install evidence record tied to the merge commit.

- [ ] **Step 1: Push the implementation branch and open/update the Draft PR**

Use intentional commits, no force push, and a PR body listing architecture, security boundaries, test evidence, and clean-Windows gate status.

- [ ] **Step 2: Wait for and inspect every required GitHub check**

Do not merge while any required check fails, is cancelled, or is unexpectedly skipped. Fix CI through a new reviewed commit and rerun.

- [ ] **Step 3: Execute the clean-Windows acceptance matrix**

Run Windows 11 primary, Windows 10 no-WinGet fallback, restart recovery, path collision, interrupted download, tampered archive, delayed REST, and existing-skill upgrade scenarios. Validate sanitized evidence with `acceptance/windows/validate-evidence.py`.

- [ ] **Step 4: Merge only the reviewed passing PR**

Record the merge commit. Confirm the working tree is clean, version metadata is consistent, and release archive identity matches the merge commit.

- [ ] **Step 5: Create the immutable release**

Create annotated tag `v0.5.2`, push it once, and publish the verified ZIP, `release-manifest.json`, `SHA256SUMS`, release notes, publisher manifest, and sanitized acceptance evidence. Never move the tag.

- [ ] **Step 6: Redownload and verify public assets**

Download every asset from the public release into a new temporary directory, verify all published digests and archive contents, and confirm tag/manifest/commit equality.

- [ ] **Step 7: Run the public README request from a fresh Windows account**

The tester performs no terminal command. Pass only if doctor is `ready`, the publisher saves one conversation, creates an A4 Desktop bundle, and deletes only the exact test conversation bundle.

- [ ] **Step 8: Mark `v0.5.2` latest and report**

Only after Step 7 passes, mark the release latest. Report PR, merge commit, tag, asset hashes, automated test counts, clean-Windows scenarios, local installed-skill backup paths, and any documented non-blocking P3 findings.

---

## Final Verification Commands

```powershell
$python = 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $python -m unittest discover -s tests -p 'test_*.py'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ci\run-pester-tests.ps1 -Path (Get-ChildItem tests\*.Tests.ps1).FullName -ExpectedSkipCount 0
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ci\run-all-tests.ps1 -PythonPath $python -ExpectedPythonSkipCount 4
```

Then build, verify, redownload, and reverify the exact public release assets. Evidence is valid only when it names the reviewed release commit and contains no secret or personal absolute path.
