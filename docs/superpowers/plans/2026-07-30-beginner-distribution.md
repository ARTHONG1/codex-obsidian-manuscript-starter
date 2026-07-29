# Beginner Distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a GitHub-ready Codex plugin marketplace and Windows bootstrap that safely installs a clean Obsidian manuscript workflow for a beginner.

**Architecture:** Package the manuscript workflow in a Codex plugin while keeping OS installation and per-user Obsidian configuration in PowerShell. Keep public defaults, runtime settings, and private Obsidian REST credentials separate. Every installer phase is deterministic, idempotent, and tested against local fixtures rather than a live user vault.

**Tech Stack:** PowerShell 7-compatible syntax, Windows PowerShell 5.1 compatibility, Python unittest, JSON, Codex plugin manifest, GitHub Actions.

## Global Constraints

- Windows-only first release; do not claim macOS/Linux support.
- Never include `data.json`, API keys, certificates, private keys, author paths, vault content, generated PDFs, or `__pycache__` in source or releases.
- Do not overwrite an existing vault target or install community code without explicit `-EnableCommunityPlugin` consent.
- Use a pinned Local REST release plus SHA-256; no unpinned `latest` download.
- Do not enable HTTP port 27123; verify HTTPS localhost readiness.
- Preserve user vaults during uninstall.

---

### Task 1: Create security tests before installer code

**Files:**
- Create: `tests/InstallerContract.Tests.ps1`
- Create: `tests/SecretScan.Tests.ps1`

**Interfaces:**
- Consumes: future `bootstrap/install-windows.ps1`, `dependencies.lock.json`, starter vault assets.
- Produces: failing checks for missing consent, unpinned downloads, unsafe vault overwrite, and secret-bearing files.

- [ ] Write tests that expect the installer to require `-EnableCommunityPlugin` before it can install plugin files.
- [ ] Write tests that expect a lock entry with a semantic version, HTTPS URL, and 64-character SHA-256.
- [ ] Write tests that expect installer logic to reject a non-empty target directory without `-AllowExistingEmptyVault`.
- [ ] Write repository scans that reject REST `data.json`, PEM material, private-key text, and `C:\\Users\\user` paths.
- [ ] Run the tests and confirm they fail because the implementation is absent.

### Task 2: Create the plugin marketplace package

**Files:**
- Create: `.agents/plugins/marketplace.json`
- Create: `plugins/obsidian-manuscript-publisher/.codex-plugin/plugin.json`
- Create: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/`
- Create: `plugins/obsidian-manuscript-publisher/assets/starter-vault/`

**Interfaces:**
- Consumes: the public-safe workflow files.
- Produces: a valid plugin discoverable from a GitHub marketplace.

- [ ] Scaffold the plugin with the plugin-creator helper in this repository.
- [ ] Copy only scripts and references needed by the existing manuscript workflow; remove cache files and hard-coded paths.
- [ ] Add a setup skill that runs the bootstrap and maintenance commands.
- [ ] Run plugin manifest validation and skill validation.

### Task 3: Implement safe environment resolution and starter vault creation

**Files:**
- Create: `bootstrap/lib/Environment.psm1`
- Create: `bootstrap/lib/Vault.psm1`
- Create: `bootstrap/assets/starter-vault/`
- Create: `bootstrap/install-windows.ps1`

**Interfaces:**
- `Resolve-InstallPaths [-VaultPath]` returns a user-local runtime configuration path and validated vault target.
- `Initialize-StarterVault -VaultPath <path> -AllowExistingEmptyVault` creates only empty/new directories.
- `Install-ObsidianIfMissing` returns structured phase status.

- [ ] Implement the smallest functions required by the failing tests.
- [ ] Use `winget` only when present; otherwise return the official download URL as a recoverable action.
- [ ] Create only clean starter templates and an empty registry.
- [ ] Run the contract tests to green.

### Task 4: Implement pinned Local REST installation and health checks

**Files:**
- Create: `dependencies.lock.json`
- Create: `bootstrap/lib/LocalRest.psm1`
- Create: `bootstrap/doctor.ps1`
- Create: `bootstrap/uninstall.ps1`

**Interfaces:**
- `Install-PinnedLocalRestPlugin -VaultPath <path> -EnableCommunityPlugin` verifies SHA-256 before extraction.
- `Wait-ForLocalRest -DataPath <path> -TimeoutSeconds <int>` polls HTTPS localhost readiness.
- `Test-LocalRestRoundTrip` creates, reads, and deletes one unique health note.

- [ ] Add tests for checksum mismatch, timeout, and deletion-scope safety.
- [ ] Implement download-to-temporary-file, hash verification, atomic plugin directory replacement, and explicit restricted-mode change only with consent.
- [ ] Implement a bounded readiness poll and authenticated REST round trip.
- [ ] Run the installer tests and doctor fixture tests to green.

### Task 5: Create beginner documentation and release checks

**Files:**
- Create: `README.md`
- Create: `SECURITY.md`
- Create: `LICENSE`
- Create: `.gitignore`
- Create: `.github/workflows/verify.yml`

**Interfaces:**
- Consumes: generated plugin, bootstrap commands, and tests.
- Produces: a copyable Codex prompt, explicit consent explanation, troubleshooting, update, and non-destructive uninstall instructions.

- [ ] Document the exact beginner prompt and expected three confirmations.
- [ ] Add GitHub Actions for PowerShell tests, JSON parsing, plugin validation, secret scans, and release-content exclusions.
- [ ] Run the complete local verification set and review staged files for secrets.
