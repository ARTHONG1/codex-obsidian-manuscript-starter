# v0.5.2 Wave 2 Security and Contract Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bind document parsing to immutable inspected bytes, make Local REST and path policies identical across components, and eliminate routing, manifest, skill, documentation, and privacy-contract drift.

**Architecture:** Keep security boundaries in their existing focused modules. `template_source.py` owns snapshot creation and cleanup; `analyze_template_sources.py` parses only snapshot paths. PowerShell and Python REST helpers share an explicit HTTPS loopback port contract. Environment path validation becomes one pairwise canonical operation, while routing and skill documentation become explicit-first and progressively disclosed.

**Tech Stack:** Python 3.12 standard library, Pillow/document parsers already pinned, Windows PowerShell 5.1, Pester, Python `unittest`, JSON/YAML plugin contracts.

## Global Constraints

- Wave 1 must be green before this wave begins.
- Do not change PDF, DOCX, or image parser evidence semantics except to make parser input immutable.
- Snapshot output and logs may contain safe basename, media type, size, and SHA-256 only; never source absolute paths or document prose.
- Local REST remains HTTPS `127.0.0.1`, certificate-verified, redirect-disabled, binary-safe, and without filesystem fallback.
- Preserve all historical manuscript validators and renderers.
- Never change an existing immutable candidate, template, manuscript, blog, or publication version.

---

### Task 6: Local REST readiness, curl capability, and explicit port parity

**Files:**
- Modify: `bootstrap/lib/LocalRest.psm1:174-310`
- Modify: `plugins/obsidian-manuscript-publisher/bootstrap/lib/LocalRest.psm1`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/save_via_obsidian_rest.py:79-94`
- Modify: `tests/InstallerContract.Tests.ps1`
- Modify: `tests/test_local_rest_security.py`

**Interfaces:**
- Produces: `Get-CurlExecutable -CommandResolver` returning an absolute `curl.exe` or throwing `curl_unavailable` with one safe recovery action.
- `Wait-ForLocalRest` retries missing, empty, incomplete, malformed, and not-yet-listening states until its deadline.
- Python `_connection(config_path, base_url=None)` requires `port` when `base_url` is absent and never defaults to 27124.

- [ ] **Step 1: Add failing PowerShell readiness tests**

Use a short timeout and a writer job or injected read/curl functions to present these sequences:

```text
missing → empty → "{" → JSON without crypto → complete JSON → curl success
```

Assert the function returns only after the complete state. Add tests for timeout code, missing `curl.exe`, invalid port, and no certificate. Ensure transient JSON errors do not escape before the deadline.

- [ ] **Step 2: Add failing Python port tests**

```python
def test_connection_rejects_missing_port_instead_of_defaulting(self):
    config.write_text(json.dumps({"apiKey": "secret", "crypto": {"cert": certificate}}), encoding="utf-8")
    with self.assertRaisesRegex(ValueError, "local_rest_port_missing"):
        rest._connection(config)

def test_explicit_safe_base_url_still_requires_loopback_https(self):
    config.write_text(json.dumps({"apiKey": "secret", "port": 27124, "crypto": {"cert": certificate}}), encoding="utf-8")
    with self.assertRaisesRegex(ValueError, "local_rest_origin_must_be_loopback_https"):
        rest._connection(config, "https://localhost:27124")
```

Also retain redirect, TLS, certificate, path, content-type, and byte-readback tests.

- [ ] **Step 3: Run targeted tests and confirm current failures**

Current expected defects: malformed JSON escapes immediately and Python uses 27124 when the field is absent.

- [ ] **Step 4: Implement condition polling and curl preflight**

Inside the loop, catch only expected file/JSON/property/connection readiness errors, record a non-secret `lastReason`, sleep 500 ms, and continue. Do not catch deadline cancellation or unsafe configuration errors. At timeout, throw:

```text
local_rest_not_ready: $lastReason. Keep Obsidian open, verify the Local REST plugin is enabled, and rerun doctor.
```

Resolve `curl.exe` once before network use and invoke the absolute path. Never emit the bearer key or certificate.

- [ ] **Step 5: Remove the Python port fallback**

Require an integer `1..65535`, build the base URL by interpolating the validated `$port` after `https://127.0.0.1:`, and reject a mismatching optional `base_url`. Keep custom base URLs only for explicitly injected test servers that still satisfy the existing loopback/TLS test contract.

- [ ] **Step 6: Verify root/plugin module identity and regressions**

Run Local REST Python tests, InstallerContract, archive, delete, publish, and custom-template registration tests.

- [ ] **Step 7: Commit**

```powershell
git add bootstrap/lib/LocalRest.psm1 plugins/obsidian-manuscript-publisher/bootstrap/lib/LocalRest.psm1 plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/save_via_obsidian_rest.py tests/InstallerContract.Tests.ps1 tests/test_local_rest_security.py
git commit -m "fix: align Local REST readiness and explicit port contracts"
```

---

### Task 7: Pairwise Vault, runtime, and publication path separation

**Files:**
- Modify: `bootstrap/lib/Environment.psm1:5-111`
- Modify: `plugins/obsidian-manuscript-publisher/bootstrap/lib/Environment.psm1`
- Modify: `bootstrap/lib/PublicationLibrary.psm1:11-112`
- Modify: `plugins/obsidian-manuscript-publisher/bootstrap/lib/PublicationLibrary.psm1`
- Modify: `tests/InstallerContract.Tests.ps1`

**Interfaces:**
- Produces: `Assert-InstallPathSetIsSafe -VaultPath -RuntimeRoot -PublicationRoot` returning canonical paths only when all pairwise and reparse checks pass.
- `Resolve-InstallPaths`, `Save-RuntimeConfig`, and `Get-RuntimeConfig` all call the same function.

- [ ] **Step 1: Add the complete failing overlap matrix**

For each pair `(Vault, Runtime)`, `(Vault, Publication)`, `(Runtime, Publication)`, test equality, first-parent, and second-parent. Add a reparse-point test when Windows privilege permits; make only that test an explicitly reported skip when symlink creation is unavailable.

```powershell
foreach ($case in @(
  @{ Vault=$root; Runtime=(Join-Path $root 'runtime'); Publication=$other },
  @{ Vault=(Join-Path $root 'vault'); Runtime=$root; Publication=$other }
)) {
  { Assert-InstallPathSetIsSafe -VaultPath $case.Vault -RuntimeRoot $case.Runtime -PublicationRoot $case.Publication } | Should Throw
}
```

- [ ] **Step 2: Confirm RuntimeRoot overlap currently passes incorrectly**

Run the focused Pester cases and capture the expected failure.

- [ ] **Step 3: Implement one canonical path-set validator**

Normalize separators, trim only non-root trailing separators, use ordinal-ignore-case comparisons, reject drive/profile roots where existing policy requires, and call `Assert-NoExistingReparsePoint` for existing ancestors. Check all three pairs before creating any directory.

- [ ] **Step 4: Route config reads and writes through the validator**

Schema-v1 normalization and schema-v2 load/save must reject the same overlap. Error messages name the conflicting logical roots without printing secrets.

- [ ] **Step 5: Run installer, publication, delete, and export regressions**

Expected: no path behavior changes outside newly rejected RuntimeRoot overlaps and reparse aliases.

- [ ] **Step 6: Commit**

```powershell
git add bootstrap/lib/Environment.psm1 bootstrap/lib/PublicationLibrary.psm1 plugins/obsidian-manuscript-publisher/bootstrap/lib/Environment.psm1 plugins/obsidian-manuscript-publisher/bootstrap/lib/PublicationLibrary.psm1 tests/InstallerContract.Tests.ps1
git commit -m "fix: reject every install-root overlap"
```

---

### Task 8: Immutable, hash-verified template source snapshots

**Files:**
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/template_source.py:1-106`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/analyze_template_sources.py:42-73`
- Modify: `tests/test_template_source_security.py`
- Modify: `tests/test_template_analysis_pipeline.py`

**Interfaces:**
- Produces immutable `SnapshotSource` with `safe_name`, `media_type`, `size_bytes`, `sha256`, and private staged `path` excluded from `to_manifest()`.
- Produces `TemplateSourceError(ValueError)` carrying one deterministic source error code without a path.
- Produces context manager `snapshot_source_set(paths, staging_parent=None)` yielding ordered snapshots and deleting only its exact owned directory on exit.
- `analyze_sources` dispatches extractors only with `SnapshotSource.path`.

- [ ] **Step 1: Write failing TOCTOU and privacy tests**

Add tests that:

- replace the source after inspection and require `source_changed_during_snapshot`;
- mutate the source after snapshot entry and prove extractor bytes remain unchanged;
- assert extractor paths are below a unique staging directory, not the source parent;
- assert source-analysis JSON contains no source or staging absolute path;
- reject staging parent reparse points;
- clean the owned directory on success and extractor exception;
- preserve unrelated files beside the owned directory.

- [ ] **Step 2: Run focused tests and reproduce original-path parsing**

Expected current failure: extractor receives the original `Path` selected at `analyze_template_sources.py:52`.

- [ ] **Step 3: Implement snapshot datatypes and bounded copy**

Use `tempfile.mkdtemp(prefix="codex-template-snapshot-", dir=staging_parent)`. For each inspected source, stream-copy in 1 MiB chunks while computing a destination digest, then compare destination size and digest with the initial inspection manifest. Reopen and hash the staged file once more before yielding. Refuse duplicate safe names and any reparse point.

```python
@contextmanager
def snapshot_source_set(paths, staging_parent=None):
    inspection = inspect_source_set(paths)
    if inspection["code"] != "source_set_ready":
        raise TemplateSourceError(str(inspection["code"]))
    owned = Path(tempfile.mkdtemp(prefix="codex-template-snapshot-", dir=staging_parent))
    try:
        snapshots = _copy_and_verify_sources(paths, inspection["sources"], owned)
        yield tuple(snapshots)
    finally:
        _remove_exact_owned_snapshot(owned)
```

The cleanup helper verifies name prefix, direct parent, and no reparse point before recursive deletion.

- [ ] **Step 4: Make analysis parse only snapshots**

Wrap evidence extraction in `with snapshot_source_set(paths) as snapshots:` and return `source.to_manifest()` rather than a path. Convert `TemplateSourceError` to `TemplateAnalysisError` with the same deterministic code and no chained absolute path. Observations retain their existing bounded handling.

- [ ] **Step 5: Run all custom-template tests**

Run template source, analysis, extractor, candidate, preview, registration, custom manuscript, and custom publication tests.

- [ ] **Step 6: Commit**

```powershell
git add plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/template_source.py plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/analyze_template_sources.py tests/test_template_source_security.py tests/test_template_analysis_pipeline.py
git commit -m "fix: parse templates from immutable inspected snapshots"
```

---

### Task 9: Explicit-first routing and plugin manifest contracts

**Files:**
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/select_book_template.py:10-47`
- Modify: `tests/test_book_template_routing.py`
- Modify: `plugins/obsidian-manuscript-publisher/.codex-plugin/plugin.json`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/agents/openai.yaml`
- Modify: `.agents/plugins/marketplace.json`
- Modify: `tests/test_documentation_contract.py`
- Modify: `tests/test_dependency_contract.py`

**Interfaces:**
- Explicit `requested_template_version` always wins over text markers.
- Natural-language marker detection uses case-insensitive token boundaries and cannot match V10.
- `interface.defaultPrompt` is an array of at most three strings, each at most 128 characters.
- Local marketplace source contains only `source` and `path`.

- [ ] **Step 1: Add failing routing and manifest tests**

```python
def test_explicit_v3_wins_over_legacy_text(self):
    result = router.select_book_template("V1 내용을 비교", requested_template_version=3)
    self.assertEqual(result["template_version"], 3)

def test_v10_does_not_match_v1(self):
    self.assertEqual(router.select_book_template("V10 테스트")["template_version"], 3)

def test_plugin_default_prompt_contract(self):
    prompts = manifest["interface"]["defaultPrompt"]
    self.assertIsInstance(prompts, list)
    self.assertLessEqual(len(prompts), 3)
    self.assertTrue(all(0 < len(value) <= 128 for value in prompts))
```

Add a test that local marketplace `source` has exactly `{"source", "path"}`.

- [ ] **Step 2: Run tests and confirm current failures**

Expected: V10 routes to V1, text can override explicit V3, defaultPrompt is a string, and marketplace contains `ref`.

- [ ] **Step 3: Implement deterministic routing**

Return immediately for explicit versions 1, 2, or 3. Only when `None`, use compiled patterns equivalent to `(?<![A-Za-z0-9])v1(?![0-9])` and `v2`, plus exact Korean phrases. Keep default V3.

- [ ] **Step 4: Correct manifests**

Use short, accurate prompt entries that route registration, conversation save/delete, and book/blog/custom publication without exceeding 128 characters. Keep `openai.yaml` prompt semantically aligned and below 128 characters. Remove local `ref`; release pinning remains in public installation commands.

- [ ] **Step 5: Run routing, documentation, plugin-validation, and full manuscript regressions**

Expected: historical explicit V1/V2 still route correctly and all default new A4 synthesis stays V3.

- [ ] **Step 6: Commit**

```powershell
git add plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/select_book_template.py tests/test_book_template_routing.py plugins/obsidian-manuscript-publisher/.codex-plugin/plugin.json plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/agents/openai.yaml .agents/plugins/marketplace.json tests/test_documentation_contract.py tests/test_dependency_contract.py
git commit -m "fix: make manuscript routing and plugin prompts deterministic"
```

---

### Task 10: Progressive skill routing, documentation parity, and whole-release privacy scan

**Files:**
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/SKILL.md`
- Create: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/conversation-workflow.md`
- Create: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/book-a4-workflow.md`
- Create: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/adaptive-blog-workflow.md`
- Create: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/custom-manuscript-workflow.md`
- Create: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/deletion-workflow.md`
- Create: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/legacy-book-contracts.md`
- Modify: `README.md`
- Modify: `INSTALL_PROMPT.md`
- Modify: `docs/INSTALL_GUIDE.md`
- Modify: `docs/TROUBLESHOOTING.md`
- Modify: `THIRD_PARTY_NOTICES.md`
- Modify: `tests/test_documentation_contract.py`
- Modify: `tests/SecretScan.Tests.ps1`
- Create: `tests/test_release_privacy_contract.py`

**Interfaces:**
- Top-level SKILL contains trigger-to-reference routing and global safety only; profile execution rules live in references.
- Current V3 defaults are loaded for new synthesis; legacy V1/V2 rules are loaded only for explicit legacy work or immutable historical versions.
- Privacy scan consumes `git ls-files` plus an explicit candidate-archive file list and returns a non-zero test failure on any finding.

- [ ] **Step 1: Add failing progressive-disclosure tests**

Require top-level SKILL to reference every workflow file, preserve all public trigger phrases and safety prohibitions, declare V3 default once, and stay below an agreed review ceiling of 180 nonblank lines. Require legacy V2 formulas to occur only in `legacy-book-contracts.md`.

- [ ] **Step 2: Add failing privacy tests**

Test a temporary tracked-file list and release candidate containing synthetic high-confidence GitHub/OpenAI-style tokens, bearer headers with long secrets, PEM private keys, Local REST `data.json`, certificate/key extensions, a synthetic user-profile path assembled at runtime from `$env:SystemDrive`, the literal path component `Users`, and `sample-account`, source PDFs/DOCX/images, and generated manuscript outputs. Every fixture uses temporary directories.

- [ ] **Step 3: Split SKILL without changing behavior**

Move text, do not paraphrase operational contracts unless required by an already approved v0.5.2 change. Top-level routes:

```text
register/pause/exclude → conversation-workflow.md
save/refresh → conversation-workflow.md
delete current conversation → deletion-workflow.md
new/default A4 → book-a4-workflow.md + master-editorial-profile.md
explicit historical V1/V2 → legacy-book-contracts.md
blog → adaptive-blog-workflow.md
template analyze/register/custom publish → custom-manuscript-workflow.md
desktop export → publication-library.md plus selected profile workflow
```

- [ ] **Step 4: Synchronize beginner and dependency documentation**

Describe six direct runtime packages plus a hash-locked transitive set, product-owned venv, schema-v2 resume, WinGet absence, Local REST retry, and the exact test runner. Do not update public install pins to v0.5.2 until the release task has a final tag candidate.

Update third-party notices from the final lock's package names and licenses using installed wheel metadata and official project metadata. Do not guess a license; a missing or ambiguous license blocks Wave 2 exit.

- [ ] **Step 5: Strengthen scans**

Pester enumerates tracked files using `git ls-files -z`, scans text files by allowlisted extension, and separately rejects forbidden names/extensions. Python archive tests inspect exact ZIP members and file content without extracting unsafe paths. Keep synthetic fixtures outside the repository scan root.

- [ ] **Step 6: Run skill forward tests and full Wave 2 regression**

Run documentation, skill sync, privacy, archive/delete, all book/blog/custom, Local REST, publication, and Desktop export suites. Then run the complete Python and Pester baselines.

- [ ] **Step 7: Commit**

```powershell
git add plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/SKILL.md plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references README.md INSTALL_PROMPT.md docs/INSTALL_GUIDE.md docs/TROUBLESHOOTING.md THIRD_PARTY_NOTICES.md tests/test_documentation_contract.py tests/SecretScan.Tests.ps1 tests/test_release_privacy_contract.py
git commit -m "docs: separate current workflows and strengthen privacy contracts"
```

## Wave 2 exit gate

- Template extractors receive only staged, hash-verified paths.
- Malformed Local REST configuration retries until ready or timeout.
- PowerShell and Python use the same explicit port and security contract.
- Every install-root overlap permutation is rejected.
- Explicit version requests beat text and V10 never matches V1.
- Plugin prompts and local marketplace metadata meet the documented contract.
- Top-level SKILL is a concise router and legacy rules are isolated.
- Whole-release privacy tests pass.
- Complete Python and Pester baselines have zero failures.
- Specification and code-quality reviewers report no unresolved P0/P1/P2.
