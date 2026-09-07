# v0.5.2 Wave 3 CI, Promotion, and Reproducible Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce the complete Windows verification contract in GitHub Actions, build a privacy-safe reproducible release archive with checksums, promote the installed skill with rollback, and permit GitHub release only after explicit authorization and every gate passes.

**Architecture:** Introduce small CI entry points that return trustworthy process exit codes and are used identically by local verification and GitHub Actions. Pin every external action by immutable commit in an action lock. Build release artifacts from an explicit allowlist into a temporary root, scan and install-test that root, and verify downloaded release bytes before success.

**Tech Stack:** Windows PowerShell 5.1, CPython 3.12, GitHub Actions, GitHub CLI, Git, gitleaks, SHA-256, ZIP.

## Global Constraints

- Waves 1 and 2 must be green and reviewed before this wave begins.
- CI uses temporary Vault, runtime, publication, and fake REST roots only.
- External GitHub actions must use 40-character immutable commit SHAs recorded in `ci/action-lock.json`.
- Release archives contain only allowlisted public repository files; no `.git`, worktrees, planning backups, test outputs, source documents, generated manuscripts, Vault data, or credentials.
- Pester result counts, not its process exit code, decide success.
- Push, PR, merge, tag, or release is forbidden unless the user explicitly authorizes GitHub writes in the execution session.
- Tag signing has no unsigned fallback.

---

### Task 11: Trustworthy local and CI test entry points

**Files:**
- Create: `ci/run-python-tests.ps1`
- Create: `ci/run-pester-tests.ps1`
- Create: `ci/run-all-tests.ps1`
- Create: `ci/invoke-pester-owned.ps1`
- Create: `ci/run_unittest.py`
- Create: `tests/TestRunnerContract.Tests.ps1`
- Modify: `tests/test_documentation_contract.py`
- Modify: `README.md`
- Modify: `docs/RELEASE.md`

**Interfaces:**
- `ci/run-python-tests.ps1 -PythonPath $Python312 -TestName $TestModules` exits nonzero on test failure, unexpected interpreter, missing summary, or unexpected skip; omitting `TestName` runs discovery.
- `ci/run-pester-tests.ps1 -Path $PesterFiles -ExpectedSkipCount $ExpectedSkipCount` launches Windows PowerShell 5.1, serializes Pester totals, and exits nonzero when counts do not match.
- `ci/run-all-tests.ps1` emits `artifacts/test-evidence.json` with commands and counts but no personal absolute paths.
- `ci/run_unittest.py` runs either discovery or named modules and emits `{testsRun, failures, errors, skipped, successful}` as JSON.

- [ ] **Step 1: Write failing runner-contract tests**

Create synthetic passing, failing, and skipped Pester files under `$TestDrive`, then invoke the runner and assert its exit code. Include a test proving a Pester process exit of zero plus `FailedCount = 1` becomes runner exit 1.

Add Python runner tests with a one-test pass module, one-test failure module, and unexpected skip module in a temporary directory.

- [ ] **Step 2: Confirm wrappers are missing**

Run TestRunnerContract and expect missing-script failures.

- [ ] **Step 3: Implement `run-pester-tests.ps1`**

Launch exactly:

```powershell
C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File ci\invoke-pester-owned.ps1
```

`ci/invoke-pester-owned.ps1` imports Pester 3.4.0, calls `Invoke-Pester -PassThru`, writes a small JSON result, and explicitly exits 1 when `FailedCount`, `PendingCount`, or `InconclusiveCount` is nonzero or `SkippedCount` differs from expectation.

- [ ] **Step 4: Implement Python and aggregate runners**

Validate `sys.version_info[:2] == (3, 12)` before tests. `ci/run_unittest.py` builds a `unittest.TestSuite`, executes it with `TextTestRunner`, and emits explicit counts; do not infer success from dots. Aggregate outputs into a path-neutral evidence JSON.

- [ ] **Step 5: Run runner self-tests, then the real full suite through wrappers**

Expected real baseline: all Python tests pass with only documented skips; all Pester suites pass with their explicit expected skips.

- [ ] **Step 6: Commit**

```powershell
git add ci/run-python-tests.ps1 ci/run-pester-tests.ps1 ci/run-all-tests.ps1 ci/invoke-pester-owned.ps1 ci/run_unittest.py tests/TestRunnerContract.Tests.ps1 tests/test_documentation_contract.py README.md docs/RELEASE.md
git commit -m "test: enforce Python and Pester result counts"
```

---

### Task 12: Windows CI matrix and immutable action pins

**Files:**
- Create: `ci/action-lock.json`
- Create: `ci/resolve-action-lock.ps1`
- Create: `.github/workflows/windows-ci.yml`
- Create: `tests/test_ci_contract.py`
- Modify: `dependencies.lock.json`
- Modify: `bootstrap/dependencies.lock.json`
- Modify: `plugins/obsidian-manuscript-publisher/bootstrap/dependencies.lock.json`

**Interfaces:**
- `ci/action-lock.json` maps official repository and reviewed tag to one 40-character commit SHA.
- Workflow references exactly those SHAs for checkout, Python setup, artifact upload, and gitleaks.
- CI jobs expose installer matrix cases `python311_selected`, `python313_selected`, `python_absent`, `python312_ready`, `restart_resume`, and `venv_reuse`.

- [ ] **Step 1: Add failing CI contract tests**

Parse YAML as text plus `action-lock.json` as JSON. Require `windows-latest`, every matrix case, Windows PowerShell Pester wrapper, full Python wrapper, secret scan, source/install sync, release build, clean install, and no real Vault path. Require every `uses:` value to end in a 40-hex SHA present in the lock.

- [ ] **Step 2: Confirm workflow and lock are absent**

Run `tests.test_ci_contract` and record expected failures.

- [ ] **Step 3: Resolve official action commits**

`ci/resolve-action-lock.ps1` accepts an explicit allowlist of official repositories and reviewed refs. For each entry it builds `https://api.github.com/repos/$Owner/$Repository/git/ref/tags/$Ref`, queries it with GitHub CLI, dereferences annotated tags, requires a 40-hex commit, and writes sorted JSON atomically. Review the resulting repository owner, tag, and commit before commit. Never execute code from the query response.

Pin `actions/checkout`, `actions/setup-python`, `actions/upload-artifact`, and `gitleaks/gitleaks-action`. Record the gitleaks tool/action identity in all three dependency-lock copies without changing the existing Local REST hashes.

- [ ] **Step 4: Implement the Windows workflow**

Jobs:

```text
contracts     → action pins, manifests, docs, dependency locks, privacy
installer     → six simulated installer scenarios, no system mutation
python        → setup-python 3.12, hash-locked dependencies, full unittest
pester        → Windows PowerShell 5.1 wrappers
package       → source/install sync, release build, secret scan, clean install
```

Use fake executables and `$TestDrive`/temporary roots for installer scenarios. The no-Python case removes only the test harness's candidate paths; never uninstall runner software.

- [ ] **Step 5: Validate YAML and run contract tests locally**

Run CI contract, dependency contract, secret scan, and all runner tests. Use a YAML parser only from the pinned dev environment.

- [ ] **Step 6: Commit**

```powershell
git add ci/action-lock.json ci/resolve-action-lock.ps1 .github/workflows/windows-ci.yml tests/test_ci_contract.py dependencies.lock.json bootstrap/dependencies.lock.json plugins/obsidian-manuscript-publisher/bootstrap/dependencies.lock.json
git commit -m "ci: enforce the Windows installation and security matrix"
```

---

### Task 13: Allowlisted release archive, checksums, clean install, and version metadata

**Files:**
- Create: `ci/release-allowlist.txt`
- Create: `ci/build-release.ps1`
- Create: `ci/verify-release.ps1`
- Create: `tests/test_release_package.py`
- Modify: `plugins/obsidian-manuscript-publisher/.codex-plugin/plugin.json`
- Modify: `README.md`
- Modify: `INSTALL_PROMPT.md`
- Modify: `docs/INSTALL_GUIDE.md`
- Modify: `docs/TROUBLESHOOTING.md`
- Modify: `docs/RELEASE.md`
- Modify: `docs/continuity-record.md`
- Modify: `CITATION.cff`

**Interfaces:**
- `build-release.ps1 -SourceRoot -OutputRoot -Version 0.5.2` creates `codex-obsidian-manuscript-starter-v0.5.2.zip` and `SHA256SUMS` from tracked allowlisted files only.
- `verify-release.ps1 -Archive -Checksums -TestRoot` verifies checksum, safe members, exact allowlist, privacy scans, package bootstrap identity, and clean temporary installation smoke.
- Public metadata consistently reports v0.5.2 only after the release candidate passes locally.

- [ ] **Step 1: Write failing package tests**

Test deterministic member order, normalized forward-slash names, no duplicate/case-colliding names, no absolute/traversal/reparse paths, no forbidden names, no untracked files, exact bootstrap and dependency-lock copies, checksum mismatch failure, and clean extraction into a new temporary directory.

Add a malicious synthetic ZIP with `../escape`, drive path, duplicate case, `data.json`, `.pem`, and a source PDF; each must be rejected before extraction.

- [ ] **Step 2: Confirm package scripts are absent**

Run `tests.test_release_package` and capture missing-script failures.

- [ ] **Step 3: Define and enforce the release allowlist**

Allow repository metadata and product paths only:

```text
.agents/plugins/marketplace.json
.github/workflows/windows-ci.yml
bootstrap/**
ci/action-lock.json
ci/run-*.ps1
ci/release-allowlist.txt
dependencies.lock.json
INSTALL_PROMPT.md
LICENSE
README.md
requirements.lock.txt
SECURITY.md
THIRD_PARTY_NOTICES.md
CITATION.cff
docs/INSTALL_GUIDE.md
docs/TROUBLESHOOTING.md
docs/RELEASE.md
plugins/obsidian-manuscript-publisher/**
```

Exclude tests, `.git`, `.worktrees`, planning files, backups, generated evidence, caches, and user outputs. The builder obtains candidates from `git ls-files`, applies the allowlist, and refuses any release-required file that is untracked.

- [ ] **Step 4: Build and verify in separate temporary roots**

The verifier reads ZIP members before extraction, checks paths, extracts to a unique empty root, runs privacy/package contracts there, and executes plugin/bootstrap smoke with fake REST and runtime roots. `SHA256SUMS` uses lowercase 64-hex plus two spaces and the exact archive basename.

- [ ] **Step 5: Update candidate version and beginner docs**

Set plugin version `0.5.2`; update installation prompts and examples to pin `v0.5.2`; explain managed Python 3.12 venv, hash lock, resumable stages, Local REST transient retry, and safe recovery. Keep claims limited to tests actually run. Use actual newlines in release notes.

- [ ] **Step 6: Run package, documentation, full regression, and clean-install verification**

Build twice from the same commit and require identical member manifests and content hashes. ZIP container timestamps may differ; `verify-release.ps1` records normalized content identity and exact final archive SHA for publication.

- [ ] **Step 7: Commit**

```powershell
git add ci/release-allowlist.txt ci/build-release.ps1 ci/verify-release.ps1 tests/test_release_package.py plugins/obsidian-manuscript-publisher/.codex-plugin/plugin.json README.md INSTALL_PROMPT.md docs/INSTALL_GUIDE.md docs/TROUBLESHOOTING.md docs/RELEASE.md docs/continuity-record.md CITATION.cff
git commit -m "release: prepare the verified v0.5.2 package"
```

---

### Task 14: Installed-skill promotion, independent audits, and authorized GitHub release

**Files:**
- Modify only if tests expose a defect: implementation files from Tasks 1–13.
- Create locally, never commit: `.planning/v052-final-evidence/test-evidence.json`
- Create locally, never commit: `.planning/v052-final-evidence/audit-report.md`
- Create locally, never commit: release assets under an owned temporary/output directory.

**Interfaces:**
- Consumes: verified source skill and `verify_skill_sync.py` promote mode.
- Produces: timestamped installed-skill backup, exact source/install comparison, final audit report, and optional GitHub release evidence.

- [ ] **Step 1: Run complete verification before promotion**

Run `ci/run-all-tests.ps1`, plugin validation, action/lock checks, gitleaks, secret scan, package build, package verify, and clean install. Capture counts and exit statuses. Stop on every failure or unexpected skip.

- [ ] **Step 2: Dispatch the nine independent read-only audits**

Use the audit scopes from the master plan. Reproduce every P0/P1/P2 independently. Apply fixes only through a new failing test and rerun the entire affected wave.

- [ ] **Step 3: Promote the installed skill with rollback**

First compare source and installed skill. Back up the installed destination to a timestamped sibling. Run:

```powershell
$SourceSkill = (Resolve-Path '.\plugins\obsidian-manuscript-publisher\skills\obsidian-manuscript-publisher').Path
$InstalledSkill = Join-Path $env:USERPROFILE '.codex\skills\obsidian-manuscript-publisher'
& $TestPython .\plugins\obsidian-manuscript-publisher\skills\obsidian-manuscript-publisher\scripts\verify_skill_sync.py --source $SourceSkill --destination $InstalledSkill --promote
```

Then compare again and run smoke tests from the installed copy in a temporary workspace with fake REST. If promotion or smoke fails, restore the backup and verify restored hashes. Do not touch the user's Vault or Desktop publication root.

- [ ] **Step 4: Prepare the local release candidate**

Record final commit, archive SHA-256, normalized content identity, test counts, skips, audit counts, installed backup path, and source/install equality. Verify `git status` contains only intended files and no secret or personal path.

- [ ] **Step 5: Stop unless GitHub writes are explicitly authorized**

Without authorization, report the verified local candidate and exact next command, then stop. Do not push, open a PR, merge, tag, or release.

- [ ] **Step 6: When authorized, publish through reviewed gates**

Use `superpowers:finishing-a-development-branch` and the GitHub publishing skill:

```text
push feature branch
→ open Draft PR
→ wait for every required Windows check
→ request and receive review
→ merge without force push
→ update local main from remote
→ verify merge commit
→ verify existing signing identity
→ create annotated signed v0.5.2 tag
→ push only that tag
→ create GitHub release with ZIP and SHA256SUMS
→ download both assets to a fresh temporary directory
→ verify SHA256SUMS and run verify-release.ps1 again
```

If no signing identity exists, stop before tag creation. Do not generate a key or create an unsigned fallback.

- [ ] **Step 7: Final report**

Report exact GitHub URLs only when verified, plus commits, checks, release asset hashes, re-download result, installed-skill status, backup path, audit counts, test counts, and all skips or external prerequisites.

## Wave 3 exit gate

- All local wrappers fail correctly on synthetic failures and pass on real suites.
- Windows CI covers the required installation matrix and all required checks pass.
- Every external action is pinned by reviewed immutable SHA.
- Release archive and checksum pass privacy, allowlist, clean-install, and re-download verification.
- Installed skill is exact-match verified or safely rolled back.
- Nine audits leave no unresolved P0/P1/P2.
- GitHub release occurs only with explicit authorization and an available signing identity.
