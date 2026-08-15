# Beginner One-Prompt Installation Design

## 1. Objective

Deliver a public Windows installation path for `ARTHONG1/codex-obsidian-manuscript-starter` that starts with only Codex installed and ends with a verified, immediately usable `obsidian-manuscript-publisher` skill.

The beginner performs only these actions:

1. Paste one installation request into Codex.
2. Approve one consolidated explanation covering Obsidian installation, a dedicated Vault, and the Local REST community plugin.
3. Restart Codex or Obsidian only when Codex explicitly requests it, then paste the one-line resume request.

The beginner never enters PowerShell commands, copies an API key, trusts a certificate manually, selects internal folders, edits JSON, installs Python packages, or copies plugin files.

## 2. Definition of “One-Prompt”

“One-prompt” means one initial natural-language request plus unavoidable security consent and application restart continuation. It does not mean an unattended background install that bypasses Windows, Codex, Obsidian, or community-plugin approval.

The public promise is:

> Paste one request, approve the clearly described installation, resume once if an application restart is required, and use the publisher after doctor reports `ready`.

The README must not promise a fixed duration such as “3 minutes.” Completion depends on downloads, Windows installer behavior, and application restart timing.

## 3. Supported Environment

- Windows 10 or Windows 11, x64.
- Codex desktop or Codex CLI already installed and authenticated.
- An internet connection that can reach GitHub release assets and the pinned official installers.
- A standard per-user Windows account. Administrator elevation may be requested only by an official installer when Windows requires it.
- A new dedicated Obsidian Vault. Adopting or modifying an existing Vault is outside this release.

The design must not assume that WinGet, Python, Git, GitHub CLI, Obsidian, curl on `PATH`, or an existing Codex plugin marketplace entry is available.

## 4. Beginner Experience

### 4.1 Public installation request

The GitHub landing page presents one primary request:

```text
ARTHONG1/codex-obsidian-manuscript-starter의 최신 안정 릴리스를 Windows에 처음부터 설치해줘.
나는 Codex만 설치한 초보자야. Obsidian 설치, 전용 빈 보관함 생성, Local REST 연결,
원고 스킬 설치와 doctor 검증까지 진행해줘. 기존 보관함과 설정은 건드리지 말고,
보안상 필요한 동의만 나에게 물어봐. doctor가 ready가 되기 전에는 완료라고 말하지 마.
```

Codex resolves the latest non-prerelease GitHub release, records the resolved version and commit, and installs that immutable version. It does not install from a branch head.

### 4.2 Consolidated consent

Before changing the machine, Codex asks one concise question that states:

- Obsidian may be installed from a pinned official installer.
- A new dedicated Vault will be created at the safe default location.
- The pinned Local REST community plugin will listen only on `https://127.0.0.1`.
- The plugin creates a local API key that will never be printed, copied into chat, committed, or sent externally.

Declining leaves the machine unchanged apart from verified files in a disposable temporary download directory.

### 4.3 Default locations

- Vault: `%USERPROFILE%\Documents\Codex Obsidian Manuscript`
- Runtime and resumable state: `%LOCALAPPDATA%\CodexObsidianManuscript`
- Verified publication library: the actual Windows Desktop known-folder path plus `옵시디언 원고`
- Codex skills: the current user’s resolved Codex skills directory

The user is not asked to choose a path. If a default target already contains user files, installation stops without deletion and proposes a new numbered empty path such as `Codex Obsidian Manuscript (2)`.

## 5. Architecture

The system is split into four independently testable units.

### 5.1 Release Acquisition

Responsibilities:

- Resolve the latest stable release from the exact owner/repository.
- Download the release archive, release manifest, and `SHA256SUMS` into an installer-owned temporary directory.
- Verify repository identity, immutable tag, version, archive digest, normalized ZIP paths, duplicate/case-colliding members, file allowlist, and release-manifest identity before extraction.
- Refuse branch archives, prereleases, missing checksums, digest mismatches, untracked executables, or unexpected files.

Codex may use its available shell or network capability internally. It must never ask the beginner to execute `irm | iex` or run downloaded text directly. The archive is verified before any contained script runs.

### 5.2 Codex Bootstrap

Responsibilities:

- Install `obsidian-manuscript-setup` and `obsidian-manuscript-publisher` from the verified release using an exact file allowlist.
- Back up an existing installation before atomic promotion.
- Verify source/destination file identity after promotion.
- Write only non-secret continuation state.
- Request a Codex restart if the current process cannot discover the newly installed skills.

The official Codex plugin installation route is preferred when it is available and verified in the target Codex version. A verified direct skill promotion route remains the compatibility fallback so installation does not depend on a working `codex plugin` executable or marketplace command.

### 5.3 Windows Environment Setup

Responsibilities:

- Discover supported Python 3.12 and Obsidian installations deterministically.
- Prefer WinGet when available.
- When WinGet is absent, download only pinned official Windows installers listed in `dependencies.lock.json`, verify SHA-256 and Authenticode publisher identity, and run their documented per-user silent installation mode.
- Create the product-owned Python environment and install only hash-locked wheels.
- Create the dedicated empty Vault without touching existing Vaults.
- Install and enable the pinned Local REST plugin from verified release files.
- Persist resumable stages atomically.
- Launch Obsidian with the dedicated Vault using a Windows mechanism verified by the clean-machine acceptance test.

No dependency is installed into an unrelated existing Python interpreter. No non-encrypted Local REST server is enabled.

### 5.4 Doctor and Publisher Activation

Responsibilities:

- Wait within a bounded interval for Obsidian and Local REST configuration to become ready.
- Read the API key and public certificate only inside the local process and never emit their values.
- Connect only to explicit loopback HTTPS with redirects disabled.
- Create a temporary `_system` note, read back identical bytes, and delete it.
- Verify the publisher skill’s expected version and exact file manifest.
- Verify the publication-library root without writing a user manuscript.
- Mark the installation `ready` only when all checks pass.

The final message contains only the Vault location, installed release version, doctor status, and the three first-use requests.

## 6. Resumable State Machine

The durable installation stages are:

```text
preflight
release_verified
skills_installed
consent_approved
python_ready
dependencies_ready
obsidian_ready
vault_ready
local_rest_installed
runtime_ready
obsidian_launched
doctor_verified
publisher_verified
ready
```

Every resumed run probes the real state again. A stage marker is a hint, never proof. The installer resumes from the first failed probe and does not repeat a successful destructive action.

State files contain versions, hashes, paths, stage names, and timestamps only. API keys and certificate bodies remain in the Local REST plugin’s private configuration and temporary process memory.

## 7. Failure and Recovery Contract

All failures return one stable code, a Korean beginner explanation, and one next action.

| Failure | Required behavior |
|---|---|
| Release or checksum mismatch | Stop before extraction or execution; remove only installer-owned temporary files. |
| Existing non-empty Vault target | Preserve it; select a new numbered empty default after user acknowledgment. |
| Existing publisher skill differs | Back it up; never overwrite it without verified atomic promotion. |
| Python or Obsidian install requests restart | Persist state and display the exact resume sentence. |
| Official installer unavailable | Stop with a source-specific error; do not substitute an unpinned mirror. |
| Local REST configuration incomplete | Keep Obsidian open, retry within the bounded window, then provide the resume sentence. |
| Doctor create/read/delete failure | Do not mark ready and do not fall back to direct Vault filesystem writes. |
| Publisher manifest mismatch | Restore the previous skill installation and report verification failure. |

The resume sentence is always:

```text
중단된 Codex Obsidian Manuscript Starter 설치를 이어서 진행해줘.
```

## 8. Security Invariants

- HTTPS loopback only: `https://127.0.0.1:<validated-port>`.
- No external network exposure and no non-encrypted HTTP Local REST server.
- No API key, certificate body, token, personal path inventory, Vault content, or manuscript text in logs, GitHub, release files, or chat output.
- No remote-script execution pipeline.
- No branch-head installation.
- No direct write into an existing Vault.
- No overwrite of a non-empty folder or an unverified existing plugin/skill.
- Release extraction rejects traversal, absolute paths, reparse points, duplicate names, case collisions, and unexpected binary/document assets.
- Every promoted skill and Local REST file is checked against the release manifest.
- Installer rollback touches only exact installer-owned staging and backup paths.

## 9. CI and Release Gates

The current CI is not an acceptance signal until its workflow is corrected. The final CI design must:

- Install the pinned development dependencies before Python tests.
- Use the Python executable produced by the current `setup-python` step instead of a stale exact patch path.
- Test installer scenarios through a dedicated test harness, not an unsupported production `-Scenario` parameter.
- Run Python, Pester, secret/privacy, release-package, source/install parity, and documentation-link contracts.
- Build the release archive only after all preceding jobs pass.
- Verify the archive in a new temporary root and publish its checksum as a CI artifact.

Automated CI is necessary but not sufficient because GitHub-hosted runners do not prove the complete interactive Obsidian desktop flow.

## 10. Clean-Windows Acceptance Matrix

The release is blocked until these end-to-end scenarios pass using the public installation request and public release assets:

| Scenario | Starting state | Required result |
|---|---|---|
| Windows 11 standard | Codex only, WinGet available | `ready`, project registration, conversation save, A4 generation, desktop export, bundle deletion |
| Windows 10 fallback | Codex only, WinGet unavailable | Pinned official installer fallback succeeds or returns an accurate unsupported-environment stop before mutation |
| Restart recovery | Restart after Python, Codex skill, and Obsidian stages | One resume request continues from the first incomplete stage |
| Path collision | Default Vault folder already contains files | Existing files preserved; safe numbered Vault selected |
| Offline interruption | Network removed during each download | No partial installation promoted; rerun safely resumes |
| Tampered archive | Digest or ZIP member changed | Installation stops before execution |
| Local REST delayed | Obsidian starts slowly or writes partial configuration | Bounded retry succeeds without exposing secrets |
| Existing skill | Older verified publisher installed | Backup, atomic upgrade, exact-sync verification, rollback test |

For the primary Windows 11 scenario, the tester may perform only the initial paste, consolidated consent, and requested restart continuation. Any extra terminal command is an acceptance failure.

## 11. Product-Level Smoke Test

After doctor reports `ready`, the clean-machine release test must perform the actual beginner workflow:

1. Register a temporary writing project.
2. Save the current test conversation to Obsidian.
3. Read back the raw conversation and material card through Local REST.
4. Generate one minimal validated A4 manuscript.
5. Confirm the Desktop publication bundle exists and opens.
6. Delete only the exact current conversation bundle.
7. Confirm neighboring project and system notes remain unchanged.

The smoke project and generated outputs are isolated test data and are removed only by their explicit cleanup step.

## 12. Documentation Contract

The GitHub landing page is organized for a first-time user:

1. One-sentence product description.
2. One large copyable installation request.
3. “What you will approve” in plain Korean.
4. “What Codex installs automatically.”
5. Resume request.
6. Three first-use requests.
7. A compact troubleshooting table.
8. Advanced developer and release details below the beginner section.

README and `INSTALL_PROMPT.md` must reference only a release that exists publicly. Version strings, release notes, plugin manifests, checksums, and installation examples must be checked as one release contract.

## 13. Release Procedure

1. Fix PR #6 CI and make all required checks pass.
2. Build and verify the allowlisted archive locally and in GitHub Actions.
3. Execute the clean-Windows acceptance matrix and record sanitized results.
4. Run an independent security/privacy review with no unresolved P0, P1, or P2 findings affecting installation.
5. Merge the reviewed PR into `main`.
6. Create an annotated immutable `v0.5.2` tag at the reviewed merge commit.
7. Publish the archive, manifest, `SHA256SUMS`, release notes, and sanitized acceptance evidence.
8. Redownload every public asset and verify its digest and archive contents.
9. Run the README installation request from a fresh Windows account against the public release.
10. Mark `v0.5.2` latest only after the public-install retest passes.

Moving an existing tag, force-pushing the release commit, publishing from a dirty tree, or releasing with failed/skipped required checks is prohibited.

## 14. Acceptance Criteria

The feature is complete only when all of the following are true:

- A new user starts with Codex only and enters no shell command.
- The only user interactions are the initial request, consolidated installation consent, and a restart continuation if requested.
- Obsidian, the dedicated Vault, Local REST, runtime dependencies, setup skill, and publisher skill are installed and verified.
- Doctor passes create/read/delete over loopback HTTPS.
- The actual publisher workflow saves a conversation and produces a verified desktop manuscript bundle.
- Existing Vaults, skills, and user files are preserved.
- All automated CI and clean-Windows acceptance gates pass.
- The README command references a real immutable public release.
- The public release can be redownloaded and installed using only its published instructions.

## 15. Explicit Non-Goals

- Adopting an existing Obsidian Vault.
- macOS or Linux installation.
- Completely unattended installation without user consent.
- Automatic publishing to Naver, Tistory, or WordPress.
- Cloud storage of API keys, certificates, conversations, or manuscripts.
- Supporting arbitrary third-party Obsidian REST plugins or unpinned mirrors.
