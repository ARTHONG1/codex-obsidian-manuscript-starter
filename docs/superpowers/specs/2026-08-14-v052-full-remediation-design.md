# v0.5.2 Full Remediation Design

## Status

Approved in conversation on 2026-08-14. This document defines the implementation boundary for v0.5.2. It does not itself authorize GitHub writes, tag creation, or a release.

## Purpose

Resolve every verified P1, P2, and P3 issue from the v0.5.1 release audit without redesigning the manuscript product. The release must install safely on a Windows account where Codex is present but Python, Obsidian, and supporting packages may be absent, and it must preserve every existing archive, deletion, manuscript, blog, custom-template, Local REST, image, and Desktop publication contract.

## Baseline and recovery point

The design baseline is public v0.5.1 at `origin/main` commit `c505046ce0e8b397ace07eb266c8127ecb820602`.

Verified baseline:

- bundled Python 3.12.13: 281 tests passed, 2 skipped;
- Windows PowerShell 5.1 with Pester 3.4.0: 46 installer-contract tests passed;
- Windows PowerShell 5.1 with Pester 3.4.0: 3 secret-scan tests passed.

The two Python skips are existing environment-dependent skips and must remain visible. Pester 3.4.0 is not a supported test runner under PowerShell 7 for this repository: it falsely reports `Should Throw` failures. CI and release scripts must invoke the Pester suite under Windows PowerShell 5.1, or upgrade the repository and tests to a separately reviewed Pester version. v0.5.2 uses the former to avoid changing test semantics during remediation.

Planning and audit files have a verified local backup outside the repository. Its exact location and manifest remain in the local planning record and must never enter a public commit or release archive.

## Non-goals

- Do not redesign book, blog, or custom-manuscript content or layout.
- Do not rewrite immutable historical `v0.N` or `t0.N` outputs.
- Do not change conversation identity, archive, refresh, or deletion semantics.
- Do not add a Vault filesystem fallback when Local REST is unavailable.
- Do not move or replace the existing v0.5.1 tag.
- Do not generate a signing key or expose signing material.
- Do not publish from this design-only branch.

## Release strategy

Implement three independently verified waves on one isolated v0.5.2 feature branch, then integrate them through one reviewed pull request.

1. Managed Python runtime and resumable installer.
2. Security and cross-component contract consistency.
3. CI, release reproducibility, documentation, and supply-chain gates.

Each wave uses test-driven development and small commits. A later wave may not hide or defer a regression introduced by an earlier wave.

## Wave 1: managed Python runtime

### Interpreter discovery

The installer requires CPython 3.12. It probes candidates in deterministic order and validates each by executing a version probe:

1. a previously verified runtime recorded in schema-v2 runtime configuration;
2. `py -3.12` when the launcher exists;
3. `python` only when the probe reports 3.12;
4. known per-user and system installation locations;
5. a newly installed 3.12 discovered by repeating the same probes.

The first executable named `python` is never trusted by name or PATH position. Existing Python 3.11, 3.13, or another application-owned Python is not upgraded, modified, or used for runtime dependency installation.

### Python installation

When no valid 3.12 interpreter exists, the installer may use WinGet to install the pinned Python 3.12 package after the existing installation consent flow. It then re-discovers the executable from the filesystem and launcher rather than relying on the current process PATH.

If WinGet is absent, the installer returns a structured, actionable status with the official Python installation route and stops. It does not download and execute an unverified bootstrap command. If a restart is needed, it returns `python_installed_restart_required` and records the resumable stage.

### Dedicated virtual environment

Runtime packages are installed only into a product-owned virtual environment under:

`%LOCALAPPDATA%/CodexObsidianManuscript/venv`

A replacement environment is built in an installer-owned staging directory. It is promoted only after all of these checks pass:

- interpreter reports Python 3.12;
- required imports succeed;
- installed versions match the lock contract;
- a runtime probe completes;
- the requirements-lock hash matches the recorded value.

The active environment is not deleted before its replacement passes. Promotion failure preserves or restores the previous verified environment.

### Locked dependencies

Runtime dependencies use exact versions and hashes in a dedicated lock file. The install command requires hashes and refuses dependency drift. Development-only dependencies remain separate. Any change to the runtime lock requires dependency-contract tests and third-party notice review.

### Runtime schema v2

The non-secret runtime configuration records:

- `schemaVersion: 2`;
- canonical Vault path;
- canonical Local REST `data.json` path;
- canonical Desktop publication root;
- verified base Python executable;
- verified venv root and Python executable;
- requirements-lock hash;
- last completed installer stage;
- installation state format version.

It never stores the Local REST API key, certificate contents, private keys, source document paths, or user manuscript content.

Schema-v1 migration validates all paths, preserves a timestamped backup, writes schema v2 through a temporary file and atomic replacement, and leaves schema v1 intact on failure.

## Installer state machine

The installer uses these ordered stages:

```text
preflight
→ base_python_ready
→ venv_ready
→ dependencies_ready
→ vault_ready
→ local_rest_ready
→ runtime_ready
→ doctor_verified
→ ready
```

Stage transitions are idempotent. Each successful transition is written atomically. Restarting Codex or Obsidian resumes from the last verified stage and revalidates the evidence for that stage before continuing.

No stage may claim success merely because a file exists. The stage probe must verify the file or service contract. A failed candidate operation never overwrites a previously verified runtime, existing Vault, existing Local REST credentials, or existing publication library.

## Wave 2: security and contract consistency

### Immutable input snapshot

PDF, DOCX, PNG, JPG, JPEG, and WEBP inputs remain untrusted. Before parsing, the analysis pipeline:

1. resolves the exact candidate input set and applies existing count and size limits;
2. rejects paths outside the allowed input contract, path traversal, absolute-path injection in metadata, UNC indirection, and reparse-point traversal;
3. copies each source into a unique installer-owned staging directory;
4. computes the source and staged SHA-256 values and requires equality;
5. passes only the staged file path to the parser;
6. records only safe basename, media type, byte size, and SHA-256 in the candidate manifest;
7. removes only the exact owned staging directory after use.

The parser never reopens the original source after the snapshot is accepted. Candidate and approved template immutability remain unchanged.

### Local REST readiness

The Local REST readiness loop treats these as transient until the deadline:

- missing `data.json`;
- an empty file;
- incomplete JSON;
- malformed JSON while Obsidian is writing;
- missing port, certificate, or API-key field;
- connection refusal while Obsidian starts.

At the deadline it returns a structured diagnostic naming the missing or invalid condition and one safe recovery action. It does not fall back to direct Vault writes.

The PowerShell path performs a `curl.exe` capability preflight before using it and produces an actionable error when it is unavailable. Python and PowerShell REST clients both require an explicit, validated HTTPS port from configuration; neither silently falls back to a different port. All writes retain binary-safe content types and byte-for-byte readback verification.

### Path separation

Vault, runtime root, and Desktop publication root are canonicalized and compared pairwise. The installer and configuration loader reject:

- equality;
- either path being an ancestor or descendant of another;
- filesystem and user-profile roots already prohibited by the publication contract;
- reparse points that cause an otherwise distinct path to resolve into an overlapping tree.

Delete and cleanup operations remain scoped to installer-owned temporary directories, one exact health-check note, one exact conversation-ID bundle, or a verified candidate environment.

### Profile and version routing

Explicit structured inputs win over natural-language inference:

1. explicit profile;
2. explicit template version;
3. explicit registered custom-template name and version;
4. natural-language inference only for unspecified fields.

Version inference uses token boundaries, so V1 does not match V10 or unrelated text. `defaultPrompt`, README examples, SKILL routing, and validators must describe the same supported commands.

### Skill-generation separation

The top-level SKILL remains a concise current-command router. Historical V1, V2, V3, and custom-manuscript details move behind progressive-disclosure references. Current synthesis rules must not accidentally load legacy generation instructions. Historical validation and rendering code remains available for immutable older packages.

### Privacy and package scope

Secret and privacy scans cover the complete tracked release surface and the generated release archive, including scripts, workflow files, examples, tests, lock files, plugin manifests, and documentation. They reject API keys, Local REST `data.json`, certificates, private keys, personal absolute paths, generated user manuscripts, copied source documents, and unintended binary assets.

The marketplace manifest must not contain a local development branch or worktree reference. All public install references resolve to the intended immutable release.

## Wave 3: CI and release reproducibility

### GitHub Actions

The Windows workflow runs on `windows-latest` and includes independently visible jobs or steps for:

- selected Python 3.11 present before installation;
- selected Python 3.13 present before installation;
- simulated no-Python discovery;
- Python 3.12 managed-runtime creation;
- restart and resume state;
- verified venv reuse and failed-candidate rollback;
- full Python unittest discovery;
- Windows PowerShell 5.1 Pester installer and secret contracts;
- plugin and manifest validation;
- source-to-install-candidate exact synchronization;
- gitleaks and repository-specific privacy scans;
- package allowlist and dependency/license checks;
- release archive creation and clean-folder installation reproduction.

Tests use temporary Vaults, fake Local REST servers, and disposable publication roots. They never use a developer's real Vault, Desktop publication library, API key, or certificate.

### Test result enforcement

The workflow must translate framework result objects into non-zero process exit codes. Pester's process exit code alone is not trusted. A non-zero failed count, an unexpected skip, an incomplete test run, a warning designated as release-blocking, or a missing report blocks the job.

Only pre-documented environment-dependent skips are permitted. Every skip appears in the release evidence.

### Release artifacts

The release candidate contains only the allowlisted public files. It produces:

- the plugin/repository installation archive;
- `SHA256SUMS`;
- machine-readable test and package evidence where supported;
- human-readable release notes with actual newlines.

The release process downloads the published assets again and verifies their SHA-256 values against `SHA256SUMS` before declaring success.

### Tag signing

If the release environment already has a usable signing identity, create an annotated signed tag. If no signing identity is available, do not generate a key, disclose secret material, or silently downgrade to an unsigned final release. Stop before tag/release and report the exact unmet signing prerequisite.

## Required test matrix

### Installer and runtime

- no Python, Python 3.11 only, Python 3.13 only, and valid Python 3.12;
- WinGet unavailable;
- restart required after Python installation;
- Codex and Obsidian restart/resume;
- valid existing venv reuse;
- stale lock hash and dependency mismatch;
- candidate venv failure and rollback;
- schema-v1-to-v2 migration success and atomic failure recovery.

### Input and template security

- normal PDF, DOCX, and image inputs, both separately and combined;
- source mutation between discovery and copy;
- staged hash mismatch;
- PDF JavaScript, Actions, and embedded files;
- DOCX macros, external relationships, traversal, excessive entries, expansion limits, and compression-ratio limits;
- excessive image dimensions and metadata;
- absolute paths, UNC paths, `file:` URLs, external URLs, and reparse-point traversal;
- unsafe input blocked before preview and registration.

### Local REST and path safety

- missing, empty, partial, malformed, then valid `data.json` transitions;
- timeout diagnostics;
- missing `curl.exe`;
- missing and mismatched explicit ports;
- text, JSON, PNG, image, and PDF binary round trips;
- all Vault/runtime/publication equality and ancestor/descendant permutations;
- exact current-conversation deletion and no neighboring deletion.

### Routing and documentation

- explicit profile and version precedence;
- V1 versus V10;
- custom template exact version selection;
- current SKILL versus legacy reference isolation;
- README, `defaultPrompt`, installer, doctor, and error-recovery command agreement;
- absence of local marketplace refs and personal paths.

### Regression

- exact conversation archive and material-card refresh;
- exact current-conversation bundle deletion;
- project registration, exclusion, and pause;
- `book_a4` V1, V2, and V3;
- `adaptive_blog`;
- `custom_manuscript` candidate, approval, immutable template, manuscript, publish, and export flows;
- image generation and validation contracts;
- immutable `v0.N` and `t0.N` allocation;
- Local REST byte readback;
- Desktop verified-publication export.

## Installation promotion

Only after the full suite and independent review pass:

1. back up the installed skill under a timestamped path;
2. copy only the reviewed allowlist from the repository candidate;
3. run source/install exact-match verification;
4. run installed-skill smoke tests in a temporary workspace with fake Local REST;
5. restore the backup immediately if promotion or smoke verification fails.

The promotion process does not modify the user's Vault or Desktop publication library during testing.

## Review and release gates

Every implementation task follows red-green-refactor and receives a specification review and code-quality review. Final read-only audits cover installer/runtime, input security, Local REST, path safety, routing, regression, dependencies/licenses, privacy, and release supply chain.

Completion requires:

- zero P0 and P1 findings;
- zero unresolved P2 findings unless the user explicitly chooses to defer and no release is produced;
- zero test failures;
- only documented skips;
- exact source/install-candidate synchronization;
- clean release-archive reproduction;
- no secret, private path, Vault data, source document, or generated user output in Git;
- all required GitHub checks passing before merge;
- release asset re-download and checksum verification.

GitHub push, pull request, merge, tag, and release remain separately authorized actions. Force push, existing-tag movement, unsigned fallback, and user-data publication are forbidden.

## Acceptance criteria

- A Windows beginner with Codex but without Python or Obsidian can follow one resumable installer flow without modifying a system Python installation.
- Python 3.11 or 3.13 on PATH cannot divert the installer from the verified Python 3.12 runtime.
- Interrupted installation resumes from verified state without overwriting existing Vault or Local REST credentials.
- Input parsing is bound to an immutable, hash-verified snapshot.
- Local REST tolerates transient configuration writes but never falls back to direct Vault writes.
- Vault, runtime, and publication trees cannot overlap in any direction.
- Explicit manuscript profile and version requests route deterministically.
- CI enforces Python, Pester, secret, package, synchronization, and clean-install tests.
- Existing archive, delete, book, blog, custom-template, image, publication, and Desktop export behavior remains compatible.
- A release is impossible when tests, checksums, required checks, privacy scans, or signing prerequisites fail.
