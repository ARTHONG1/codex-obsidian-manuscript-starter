# v0.5.2 Wave 1 Managed Runtime and Resumable Installer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make setup reliably select Python 3.12, install dependencies only into a verified product-owned venv, and resume safely across Codex or Obsidian restarts.

**Architecture:** Add a focused `PythonRuntime.psm1` beside the existing bootstrap modules. Keep path/config/state ownership in `Environment.psm1`, but upgrade it to schema v2 and atomic migration. The installer becomes an idempotent state-machine coordinator and the doctor always probes the exact venv executable recorded in runtime configuration.

**Tech Stack:** Windows PowerShell 5.1, Pester 3.4.0, CPython 3.12, `venv`, pip `--require-hashes`, Python standard-library lock generation, JSON.

## Global Constraints

- Apply every canonical bootstrap change byte-identically to `plugins/obsidian-manuscript-publisher/bootstrap/`.
- Do not install packages into `python`, `py`, or another pre-existing interpreter.
- Do not trust current-process PATH after WinGet installation; rediscover the executable.
- Build a candidate venv and promote it only after version, imports, package versions, and lock hash pass.
- Preserve the prior verified venv and schema-v1 runtime file until schema-v2 promotion succeeds.
- Keep API keys and certificates out of runtime and stage files.
- Run Pester through Windows PowerShell 5.1 and inspect `FailedCount`.

---

### Task 1: Hash-complete runtime dependency lock

**Files:**
- Create: `ci/generate-requirements-lock.py`
- Create: `requirements.lock.txt`
- Create: `plugins/obsidian-manuscript-publisher/requirements.lock.txt`
- Modify: `requirements-dev.txt`
- Modify: `tests/test_dependency_contract.py:8-40`
- Modify: `tests/InstallerContract.Tests.ps1:190-260`

**Interfaces:**
- Consumes: direct runtime pins in `requirements.txt`.
- Produces: `requirements.lock.txt` containing every resolved Windows CPython 3.12 runtime distribution as `name==version --hash=sha256:` followed by a 64-character lowercase digest; packaged copy must be byte-identical.
- Produces: `ci/generate-requirements-lock.py INPUT_REQUIREMENTS WHEEL_DIRECTORY OUTPUT_LOCK` for reproducible maintainer regeneration from previously downloaded wheels.

- [ ] **Step 1: Add failing dependency-lock tests**

Add tests that parse logical requirement entries and require exact versions and at least one SHA-256 per entry:

```python
def logical_lock_entries(text: str) -> list[str]:
    return [block.replace("\\\n", " ") for block in text.split("\n\n") if block.strip() and not block.lstrip().startswith("#")]

def test_runtime_lock_is_hash_complete_and_packaged_identically(self):
    root_lock = ROOT / "requirements.lock.txt"
    packaged_lock = ROOT / "plugins/obsidian-manuscript-publisher/requirements.lock.txt"
    self.assertEqual(root_lock.read_bytes(), packaged_lock.read_bytes())
    entries = logical_lock_entries(root_lock.read_text(encoding="utf-8"))
    self.assertTrue(entries)
    for entry in entries:
        self.assertRegex(entry, r"^[A-Za-z0-9_.-]+==[^\s]+")
        self.assertRegex(entry, r"--hash=sha256:[0-9a-f]{64}")
```

Add a Pester contract requiring both bootstrap trees to resolve the packaged lock instead of plain `requirements.txt`.

- [ ] **Step 2: Run tests and confirm the intended failure**

Run:

```powershell
& $TestPython -m unittest tests.test_dependency_contract -v
& .\ci\run-pester-tests.ps1 -Path .\tests\InstallerContract.Tests.ps1
```

Before `ci/run-pester-tests.ps1` exists, invoke Windows PowerShell 5.1 directly and inspect the returned `FailedCount`. Expected failure: missing `requirements.lock.txt` and installer references to `requirements.txt`.

- [ ] **Step 3: Implement deterministic lock generation**

`ci/generate-requirements-lock.py` must:

```python
def wheel_identity(path: Path) -> tuple[str, str]:
    with zipfile.ZipFile(path) as archive:
        metadata_name = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
        message = email.message_from_bytes(archive.read(metadata_name))
    return canonicalize_name(message["Name"]), message["Version"]

def build_lock(wheels: list[Path]) -> str:
    grouped: dict[tuple[str, str], list[str]] = {}
    for wheel in wheels:
        identity = wheel_identity(wheel)
        grouped.setdefault(identity, []).append(hashlib.sha256(wheel.read_bytes()).hexdigest())
    return render_sorted_hash_entries(grouped)
```

The script refuses duplicate versions for one canonical name, non-wheel files, missing direct requirements, or an empty wheel set. Generate the wheel set with the implementation environment's verified Python 3.12:

```powershell
$WheelRoot = Join-Path $env:TEMP ("codex-v052-lock-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $WheelRoot | Out-Null
& $TestPython -m pip download --only-binary=:all: --platform win_amd64 --python-version 312 --implementation cp --abi cp312 --requirement .\requirements.txt --dest $WheelRoot
& $TestPython .\ci\generate-requirements-lock.py .\requirements.txt $WheelRoot .\requirements.lock.txt
Copy-Item .\requirements.lock.txt .\plugins\obsidian-manuscript-publisher\requirements.lock.txt
```

Do not commit `$WheelRoot` or any wheel.

- [ ] **Step 4: Verify a clean hash-required installation**

```powershell
$ProbeVenv = Join-Path $env:TEMP ("codex-v052-lock-probe-" + [guid]::NewGuid().ToString("N"))
& $TestPython -m venv $ProbeVenv
& (Join-Path $ProbeVenv 'Scripts\python.exe') -m pip install --require-hashes --only-binary=:all: -r .\requirements.lock.txt
& (Join-Path $ProbeVenv 'Scripts\python.exe') .\bootstrap\verify_python_runtime.py
```

Expected: probe JSON has `ready: true` and Python `3.12`.

- [ ] **Step 5: Run dependency and installer regressions**

Run `tests.test_dependency_contract`, `tests.test_python_runtime_probe`, and the complete InstallerContract suite. Expected: all pass.

- [ ] **Step 6: Commit**

```powershell
git add ci/generate-requirements-lock.py requirements.lock.txt requirements-dev.txt plugins/obsidian-manuscript-publisher/requirements.lock.txt tests/test_dependency_contract.py tests/InstallerContract.Tests.ps1
git commit -m "build: lock Windows runtime dependencies by hash"
```

---

### Task 2: Deterministic Python 3.12 discovery and installation boundary

**Files:**
- Create: `bootstrap/lib/PythonRuntime.psm1`
- Create: `plugins/obsidian-manuscript-publisher/bootstrap/lib/PythonRuntime.psm1`
- Create: `tests/PythonRuntimeContract.Tests.ps1`
- Modify: `tests/InstallerContract.Tests.ps1:45-130`

**Interfaces:**
- Produces: `Find-Python312 -ExplicitPython $ExplicitPython -CommandResolver $CommandResolver -VersionProbe $VersionProbe -LocalAppDataRoot $LocalAppDataRoot -ProgramFilesRoot $ProgramFilesRoot` returning `{ Ready, Reason, Python, PythonVersion, Source }`.
- Produces: `Install-Python312 -WingetPath $WingetPath -ProcessRunner $ProcessRunner` returning `{ Status, Recovery }` without mutating another interpreter.
- Consumes: no runtime config yet; this task establishes base-interpreter selection only.

- [ ] **Step 1: Write failing discovery tests**

Cover these cases with injected candidate and probe scriptblocks:

```powershell
It "skips Python 3.11 on PATH and selects py -3.12" {
    $result = Find-Python312 -CommandResolver $resolver -VersionProbe $probe
    $result.Ready | Should Be $true
    $result.Python | Should Be 'C:\Python312\python.exe'
}

Add three explicit fixtures beside that test: one resolver exposing only a 3.13 probe and expecting `Ready = $false`; one stateful resolver that exposes 3.12 only after `Install-Python312` returns `python_installed`; and one resolver that stays empty after installation and expects `python_installed_restart_required`. Invoke `Install-Python312 -WingetPath $null` in a fourth test and require `python_install_manual_required` without calling the process runner.
```

Use fake paths under `$TestDrive`; do not invoke real WinGet or Python.

- [ ] **Step 2: Run the new suite and confirm missing-module failure**

Run with Windows PowerShell 5.1 and assert `FailedCount > 0` because `PythonRuntime.psm1` does not exist.

- [ ] **Step 3: Implement candidate discovery**

Candidate order must be explicit path, `py -3.12`, `python`, per-user known paths, then Program Files known paths. The version probe executes:

```powershell
& $Candidate -c 'import json,sys; print(json.dumps({"major":sys.version_info[0],"minor":sys.version_info[1],"executable":sys.executable}))'
```

Accept only major `3`, minor `12`, exit code zero, an absolute existing executable, and a parsed executable resolving to the same candidate. Deduplicate canonical paths case-insensitively.

- [ ] **Step 4: Implement the WinGet boundary**

Call only:

```powershell
winget.exe install --id Python.Python.3.12 --exact --accept-source-agreements --accept-package-agreements
```

Return structured status; never run pip here. On success, the caller must invoke `Find-Python312` again. Do not modify PATH or the registry.

- [ ] **Step 5: Verify discovery and packaged-copy identity**

Run `PythonRuntimeContract.Tests.ps1` and add an InstallerContract assertion that root and packaged `PythonRuntime.psm1` are byte-identical.

- [ ] **Step 6: Commit**

```powershell
git add bootstrap/lib/PythonRuntime.psm1 plugins/obsidian-manuscript-publisher/bootstrap/lib/PythonRuntime.psm1 tests/PythonRuntimeContract.Tests.ps1 tests/InstallerContract.Tests.ps1
git commit -m "feat: discover Python 3.12 without mutating system runtimes"
```

---

### Task 3: Candidate venv creation, verification, and rollback

**Files:**
- Modify: `bootstrap/lib/PythonRuntime.psm1`
- Modify: `plugins/obsidian-manuscript-publisher/bootstrap/lib/PythonRuntime.psm1`
- Modify: `tests/PythonRuntimeContract.Tests.ps1`
- Modify: `bootstrap/verify_python_runtime.py:31-109`
- Modify: `plugins/obsidian-manuscript-publisher/bootstrap/verify_python_runtime.py:31-109`
- Modify: `tests/test_python_runtime_probe.py:18-end`

**Interfaces:**
- Produces: `Get-ManagedVenvPaths -RuntimeRoot` returning canonical `ActiveRoot`, `ActivePython`, and unique `CandidateRoot`.
- Produces: `New-VerifiedManagedVenv -BasePython -RuntimeRoot -RequirementsLockPath -ProcessRunner` returning `{ Ready, BasePython, Python, VenvRoot, RequirementsHash, Reused, Backup }`.
- Produces: `Test-ManagedPythonRuntime -PythonPath -RequirementsHash -ProbePath` returning the existing probe fields plus `RequirementsHash`.

- [ ] **Step 1: Write failing venv tests**

Add tests proving:

- pip receives `--require-hashes --only-binary=:all:` and the candidate venv Python, never base Python;
- a valid active venv with matching lock hash is reused;
- a stale lock builds a candidate;
- failed candidate verification leaves active venv byte-identical;
- successful promotion preserves a backup until post-promotion verification succeeds;
- a failed post-promotion probe restores the backup;
- candidate and backup paths remain children of canonical runtime root and reject reparse points.

Use an injected `ProcessRunner` that records executable and arguments and creates minimal fake files.

- [ ] **Step 2: Confirm the tests fail on missing functions**

Run only `PythonRuntimeContract.Tests.ps1` and `tests.test_python_runtime_probe`.

- [ ] **Step 3: Extend the Python probe**

Accept optional `--requirements-hash` whose value matches `^[0-9a-f]{64}$` and include it in JSON. Keep package version and import checks. Reject a non-3.12 interpreter before importing optional packages.

- [ ] **Step 4: Implement candidate venv lifecycle**

Required command sequence:

```text
$BasePython -m venv $CandidateRoot
$CandidatePython -m pip install --disable-pip-version-check --require-hashes --only-binary=:all: -r $RequirementsLockPath
$CandidatePython verify_python_runtime.py --requirements-hash $RequirementsHash
```

Use exact owned names `venv.candidate-` plus `[guid]::NewGuid().ToString("N")` and `venv.backup-` plus a separate GUID. Reject existing reparse points. Rename active to backup, candidate to active, probe active, then remove only the verified owned backup. On any exception, restore backup and remove only the exact owned candidate.

- [ ] **Step 5: Run targeted and full Wave 1 tests**

Expected: new Pester tests pass; Python probe tests pass; InstallerContract remains green.

- [ ] **Step 6: Commit**

```powershell
git add bootstrap/lib/PythonRuntime.psm1 bootstrap/verify_python_runtime.py plugins/obsidian-manuscript-publisher/bootstrap/lib/PythonRuntime.psm1 plugins/obsidian-manuscript-publisher/bootstrap/verify_python_runtime.py tests/PythonRuntimeContract.Tests.ps1 tests/test_python_runtime_probe.py
git commit -m "feat: create and roll back a verified managed venv"
```

---

### Task 4: Runtime schema v2 and atomic stage migration

**Files:**
- Modify: `bootstrap/lib/Environment.psm1:20-188`
- Modify: `plugins/obsidian-manuscript-publisher/bootstrap/lib/Environment.psm1:20-188`
- Modify: `tests/InstallerContract.Tests.ps1:490-560`
- Modify: `tests/PythonRuntimeContract.Tests.ps1`

**Interfaces:**
- `Save-RuntimeConfig -Paths -PythonRuntime` writes schema v2 atomically.
- `Get-RuntimeConfig -RuntimeConfigPath` returns canonical schema-v1 or schema-v2 data with `NeedsMigration` and never performs a write.
- `Convert-RuntimeConfigV1ToV2 -RuntimeConfigPath -Paths -PythonRuntime` creates `runtime.json.` plus a filesystem-safe UTC timestamp plus `.v1.bak`, atomically writes v2, and restores v1 on failure.
- `Set-InstallStage` accepts only the nine approved stages and writes install-stage schema v2 atomically. When runtime schema v2 already exists, it also atomically mirrors the same value into `lastCompletedStage`; the install-stage file remains authoritative before runtime config exists.

- [ ] **Step 1: Add failing schema and atomicity tests**

Test exact schema-v2 fields including `pythonExecutable`, `venvRoot`, `venvPythonExecutable`, `requirementsHash`, and `lastCompletedStage`; no `apiKey`/`cert`; v1 read compatibility; migration backup; invalid Python path rejection; stale requirements hash rejection; write failure preserving original bytes; malformed stage recovery; stage/runtime mirror consistency; and all approved stage names.

```powershell
$config = Get-Content -Raw $runtimePath | ConvertFrom-Json
$config.schemaVersion | Should Be 2
$config.pythonExecutable | Should Be $python.BasePython
$config.venvPythonExecutable | Should Be $python.Python
($config | ConvertTo-Json -Depth 8) | Should Not Match 'apiKey|BEGIN CERTIFICATE'
```

- [ ] **Step 2: Run and confirm schema-v1 expectation failures**

Run the InstallerContract and PythonRuntimeContract suites.

- [ ] **Step 3: Implement one atomic JSON writer**

Add private `Write-AtomicUtf8Json` using an owned same-directory temp file, flush/close, and `Move-Item -Force`. Validate destination parent and reject a reparse point before writing. Use it for runtime config and stage files.

- [ ] **Step 4: Implement v1 normalization and explicit migration**

`Get-RuntimeConfig` must not mutate. It returns null Python fields plus `NeedsMigration = $true` for valid v1. The installer migrates only after a managed runtime is verified. `doctor.ps1` reports `runtime_migration_required` when handed v1 rather than choosing PATH Python.

- [ ] **Step 5: Run migration and bootstrap-copy tests**

Require byte equality for both Environment modules. Run all Pester suites.

- [ ] **Step 6: Commit**

```powershell
git add bootstrap/lib/Environment.psm1 plugins/obsidian-manuscript-publisher/bootstrap/lib/Environment.psm1 tests/InstallerContract.Tests.ps1 tests/PythonRuntimeContract.Tests.ps1
git commit -m "feat: persist managed runtime schema v2 atomically"
```

---

### Task 5: Wire the resumable installer and doctor

**Files:**
- Modify: `bootstrap/install-windows.ps1:16-119`
- Modify: `bootstrap/doctor.ps1:11-36`
- Modify: `plugins/obsidian-manuscript-publisher/bootstrap/install-windows.ps1`
- Modify: `plugins/obsidian-manuscript-publisher/bootstrap/doctor.ps1`
- Modify: `tests/InstallerContract.Tests.ps1:45-end`
- Modify: `tests/PythonRuntimeContract.Tests.ps1`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-setup/SKILL.md`

**Interfaces:**
- Installer coordinates the approved nine stages and returns one summary object.
- Doctor reads schema v2 and probes `venvPythonExecutable`; it never calls bare `python`.
- Existing parameters and community-plugin consent remain compatible.

- [ ] **Step 1: Write failing installer scenario tests**

Extend `New-TestBootstrapHarness` with a fake `PythonRuntime.psm1`. Add scenarios for Python 3.11 selected, 3.13 selected, no Python, WinGet absent, restart required, successful venv creation, venv reuse, Codex restart after `base_python_ready`, Obsidian restart after `local_rest_ready`, and v1 migration.

Assert no captured command uses the discovered base interpreter followed by `-m pip install`; pip installation must use only the candidate venv interpreter.

- [ ] **Step 2: Confirm failures occur in the current installer branch**

Run InstallerContract and verify mismatch scenarios fail because the current script installs into the selected interpreter.

- [ ] **Step 3: Replace the inline Python block**

Installer order:

```powershell
$base = Find-Python312
if (-not $base.Ready) {
    $install = Install-Python312
    if ($install.Status -ne 'python_installed') { return $install }
    $base = Find-Python312
    if (-not $base.Ready) {
        return [pscustomobject]@{ Status = 'python_installed_restart_required'; Recovery = 'Restart Codex and rerun the same installer command.' }
    }
}
Set-InstallStage -Stage 'base_python_ready'
$managed = New-VerifiedManagedVenv -BasePython $base.Python -RuntimeRoot $paths.RuntimeRoot -RequirementsLockPath $lock
Set-InstallStage -Stage 'venv_ready'
Set-InstallStage -Stage 'dependencies_ready'
```

Then preserve the existing Obsidian, Vault, Local REST, publication-library, and consent sequence. Save schema v2 with `$managed`. Do not skip stage probes merely because the stage file says they completed.

- [ ] **Step 4: Make doctor use the recorded venv**

Load runtime first, reject `NeedsMigration`, and call:

```powershell
$pythonState = Test-ManagedPythonRuntime -PythonPath $runtime.venvPythonExecutable -RequirementsHash $runtime.requirementsHash
```

Keep publication and REST round-trip behavior unchanged.

- [ ] **Step 5: Verify exact packaged copies and full Wave 1 regression**

Run:

```powershell
& $TestPython -m unittest tests.test_python_runtime_probe tests.test_dependency_contract -v
& .\ci\run-pester-tests.ps1 -Path .\tests\PythonRuntimeContract.Tests.ps1
& .\ci\run-pester-tests.ps1 -Path .\tests\InstallerContract.Tests.ps1
```

Until the Wave 3 wrapper exists, use Windows PowerShell 5.1 with `-ExecutionPolicy Bypass` and fail manually on `FailedCount`.

- [ ] **Step 6: Run complete baseline before Wave 2**

Run Python discovery and both Pester files. Expected: zero failures; preserve and report the two pre-existing Python skips.

- [ ] **Step 7: Commit**

```powershell
git add bootstrap/install-windows.ps1 bootstrap/doctor.ps1 plugins/obsidian-manuscript-publisher/bootstrap/install-windows.ps1 plugins/obsidian-manuscript-publisher/bootstrap/doctor.ps1 tests/InstallerContract.Tests.ps1 tests/PythonRuntimeContract.Tests.ps1 plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-setup/SKILL.md
git commit -m "feat: resume setup with the recorded managed runtime"
```

## Wave 1 exit gate

- Python 3.11/3.13/no-Python/3.12 scenarios pass without modifying an existing interpreter.
- Clean venv install uses `--require-hashes` and passes the runtime probe.
- Runtime v1 migration is atomic and recoverable.
- Restart/resume scenarios pass.
- Root and packaged bootstrap trees are byte-identical.
- Complete Python and Pester baseline has zero failures.
- Specification and code-quality reviewers report no unresolved P0/P1/P2.
