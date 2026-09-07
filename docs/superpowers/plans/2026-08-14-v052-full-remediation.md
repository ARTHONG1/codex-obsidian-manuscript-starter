# v0.5.2 Full Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a verified v0.5.2 that installs with a managed Python 3.12 runtime, closes the audited security and contract gaps, and blocks unsafe or unreproducible GitHub releases without changing existing manuscript behavior.

**Architecture:** Implement three reviewable waves in one isolated `codex/v052-full-remediation` branch. Wave 1 owns interpreter discovery, the managed venv, runtime schema v2, and resumable setup; Wave 2 owns immutable input snapshots, Local REST and path consistency, routing, manifests, skill routing, and privacy scans; Wave 3 owns enforced Windows CI, release packaging, checksums, signing gates, installation promotion, and final regression. Each wave is independently testable and receives specification and quality review before the next begins.

**Tech Stack:** Windows PowerShell 5.1, Pester 3.4.0, CPython 3.12, Python `unittest`, JSON, Codex plugin manifests, GitHub Actions on `windows-latest`, gitleaks, Obsidian Local REST API over loopback HTTPS.

## Global Constraints

- Baseline is public v0.5.1 commit `c505046ce0e8b397ace07eb266c8127ecb820602`; never move or rewrite tag `v0.5.1`.
- Work only in a new isolated worktree and a `codex/` branch created from `origin/main`; preserve the dirty root checkout and all user files.
- Before every Python test command, resolve an absolute Python 3.12 executable from the Codex workspace dependency loader and keep the path only in the process variable `$TestPython`; never write a user-specific path to Git.
- Run Pester 3.4.0 only through Windows PowerShell 5.1. PowerShell 7 produces false `Should Throw` failures for this suite.
- Treat framework result objects as authoritative: fail when Pester `FailedCount` is nonzero even if the process returns zero.
- Existing archive, refresh, exact deletion, project registry, `book_a4` V1/V2/V3, `adaptive_blog`, `custom_manuscript`, image, immutable version, Local REST byte-readback, and Desktop publication behavior are regression-protected.
- Never test against the user's Vault, API key, certificate, Desktop publication library, installed skill, or manuscript data. Use temporary roots and fake Local REST only.
- Never add a direct Vault filesystem fallback.
- Runtime configuration stores paths, stage, interpreter, venv, and lock hash only; it never stores REST secrets or user document content.
- Do not weaken a test to accommodate implementation. Use red-green-refactor and small commits.
- GitHub push, PR, merge, tag, and release require the user's explicit approval in the execution session. Local implementation and verification do not imply that approval.
- No release while any P0/P1/P2, test failure, unexpected skip, secret finding, source/install drift, checksum mismatch, required-check failure, or signing prerequisite remains.

---

## Plan Map

Execute these documents in order:

1. [Wave 1 — Managed Runtime and Resumable Installer](2026-08-14-v052-wave1-runtime-installer.md)
2. [Wave 2 — Security and Contract Consistency](2026-08-14-v052-wave2-security-contracts.md)
3. [Wave 3 — CI, Promotion, and Reproducible Release](2026-08-14-v052-wave3-ci-release.md)

## Cross-wave interfaces

Wave 1 produces:

- `bootstrap/lib/PythonRuntime.psm1` public functions `Find-Python312`, `Install-Python312`, `Get-ManagedVenvPaths`, `New-VerifiedManagedVenv`, and `Test-ManagedPythonRuntime`;
- runtime schema v2 fields `pythonExecutable`, `venvRoot`, `venvPythonExecutable`, `requirementsHash`, and `lastCompletedStage`;
- ordered stage vocabulary `preflight`, `base_python_ready`, `venv_ready`, `dependencies_ready`, `vault_ready`, `local_rest_ready`, `runtime_ready`, `doctor_verified`, `ready`;
- a hash-complete `requirements.lock.txt` copied byte-identically into the installable plugin.

Wave 2 consumes the schema-v2 paths and produces:

- `snapshot_source_set(paths, staging_parent=None)` as the only parser entrance for untrusted template examples;
- one explicit Local REST port contract in PowerShell and Python;
- pairwise canonical separation of Vault, runtime, and publication roots;
- deterministic explicit-first manuscript routing;
- concise SKILL routing with progressive-disclosure references;
- whole-release privacy and secret scan contracts.

Wave 3 consumes both waves and produces:

- `ci/run-python-tests.ps1`, `ci/run-pester-tests.ps1`, `ci/build-release.ps1`, and `ci/verify-release.ps1`;
- `.github/workflows/windows-ci.yml` with enforced clean-install and regression jobs;
- an allowlisted release ZIP and `SHA256SUMS` that pass re-download verification;
- an installed-skill promotion result or automatic restoration of its timestamped backup.

## Mandatory review gates

After each task:

1. run the task-specific test command;
2. run its wave regression subset;
3. dispatch a specification-compliance reviewer;
4. dispatch a code-quality and security reviewer;
5. address findings using `superpowers:receiving-code-review`;
6. commit only the reviewed task files.

After each wave, run the complete Python and Pester baseline. If a failure appears, stop and use `superpowers:systematic-debugging`; do not continue into the next wave.

## Final independent audits

Dispatch nine read-only audits after Wave 3:

1. Python discovery, venv isolation, lock reproducibility, and resume behavior.
2. Runtime schema migration, atomic writes, and path separation.
3. PDF/DOCX/image snapshot and parser TOCTOU resistance.
4. Local REST polling, TLS, explicit port, binary round trip, and no-fallback behavior.
5. Explicit profile/version routing, manifest contracts, documentation, and SKILL separation.
6. Archive, delete, book, blog, custom-template, image, publication, and Desktop export regressions.
7. Dependencies, third-party notices, privacy scans, package allowlist, and generated archive contents.
8. Windows CI enforcement, Pester result handling, required checks, checksums, and signing gate.
9. Adversarial review for overclaiming, skipped scenarios, hidden private paths, secrets, or user data.

Each audit reports category, P0–P3, exact file and line, reproduction, recommended test, and uncertainty. The lead agent deduplicates findings and independently reproduces every P0/P1/P2.

## Completion evidence

Completion report must include:

- exact branch, worktree, baseline, and final commit;
- changed-file list grouped by wave;
- each test command with pass/fail/skip counts and captured exit status;
- independent audit counts and disposition;
- installed-skill backup path, promotion status, rollback status, and exact source/install comparison;
- release archive name, SHA-256, clean-install result, and re-download verification when GitHub release was explicitly authorized;
- whether push, PR, merge, tag, and release were performed;
- every remaining warning, skip, external prerequisite, or unverified claim.

Do not call the work complete when the evidence above is missing.
