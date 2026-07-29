# Codex Obsidian Manuscript Starter Design

## Goal

Ship a public Windows-first GitHub project that starts from a machine with Codex installed and guides a beginner to a verified Obsidian manuscript workflow without copying personal vault data or REST credentials.

## Supported first release

- Windows 10 or Windows 11.
- Codex desktop app or Codex CLI with plugin marketplace support.
- Obsidian desktop only; the Local REST API dependency is not a mobile path.

## Architecture

The repository is a Codex plugin marketplace. Its plugin bundles the reusable manuscript skill, starter-vault assets, and maintenance scripts. A separate Windows bootstrap script installs or detects Obsidian, creates a new user-owned vault, installs a pinned Local REST plugin release after explicit consent, starts Obsidian, waits for local configuration, and runs a real REST health check.

The plugin and bootstrap never ship an existing vault, `data.json`, API key, certificate, private key, conversations, manuscripts, generated images, or author-specific absolute path. Runtime configuration stores only the selected vault path; the REST bearer key remains inside the user's Obsidian plugin data file.

## User journey

1. The beginner asks Codex to install the repository using the copyable README prompt.
2. Codex reviews and runs `bootstrap/install-windows.ps1`.
3. The bootstrap obtains explicit consent before enabling community plugin code, then installs Obsidian when needed and creates a new vault without overwriting an existing folder.
4. The bootstrap starts Obsidian, polls for Local REST readiness, and creates/reads/deletes a uniquely named temporary health note.
5. The bootstrap installs the Codex plugin marketplace entry and prints a new-chat instruction.
6. In a new Codex task, the user invokes the bundled setup skill to register the first manuscript project.

## Security boundaries

- HTTPS on `127.0.0.1:27124` only; do not enable the insecure HTTP endpoint.
- Pin upstream Local REST plugin version and SHA-256 in a lock file; reject mismatches.
- Use an explicit `-EnableCommunityPlugin` switch for code execution consent.
- Reject existing non-empty vault targets unless the user explicitly selects a separate migration flow.
- Limit all cleanup to installer-owned temporary directories and one uniquely named health-check note.
- Preserve user vaults and manuscripts on uninstall by default.
- Include `.gitignore`, secret scanning, and release-time content checks that reject `data.json`, certificates, private keys, author paths, and generated manuscripts.

## Failure model

Every phase returns structured JSON with a phase name, status, safe next action, and diagnostics path. The bootstrap uses condition polling with a deadline rather than fixed sleeps. Failures leave existing user data unchanged and never claim completion without a successful authenticated REST round trip.

## Distribution

Use a repo marketplace during public beta. A future submission to the universal plugin directory is optional and separate from GitHub release work.
