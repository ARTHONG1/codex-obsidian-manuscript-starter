# Desktop Verified Manuscript Publication Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a desktop `옵시디언 원고` publication library that exports only freshly validated `book_a4` and `adaptive_blog` packages into safe, copy-ready, versioned bundles without moving or weakening the Obsidian Vault.

**Architecture:** Keep the Vault and immutable local version folder as sources of record. A new deterministic Python exporter validates one explicitly selected version, derives copy-ready text and portable assets in a sibling staging directory, verifies every staged hash, then promotes it to `00 최신본` while preserving immutable history. A focused PowerShell module resolves the Windows Desktop known folder, stores the optional non-secret `publicationRoot`, creates the Vault-folder shortcut, and is mirrored in the repository and installable plugin bootstrap trees.

**Tech Stack:** Python 3.12 standard library, existing Pillow/ReportLab renderers and validators, `unittest`, Windows PowerShell 5.1-compatible modules, Pester, static HTML5, JSON, Markdown.

## Global Constraints

- Keep the configured Vault in place; never move, rename, or write directly into it for this feature.
- Resolve the default root through Windows `DesktopDirectory` known-folder resolution and name it exactly `옵시디언 원고`; never hard-code `C:\Users\<username>\Desktop`.
- Export only one explicitly selected immutable `v0.N` source package per invocation.
- Require `status: ready`, current `validated_inputs`, exact profile allowlists, valid asset hashes, and successful rendered-output checks before changing `00 최신본`.
- Keep `book_a4` and `adaptive_blog` profile trees separate. `book_a4` includes PDF; `adaptive_blog` never includes or creates PDF.
- Copy only reader-facing files and manifest-listed images. Never copy Local REST credentials, certificates, private keys, conversation archives, arbitrary adjacent files, or private source attachments.
- Reject traversal, absolute/UNC/drive-prefixed asset paths, Windows reserved names, trailing-dot/space aliases, symlinks, junctions, reparse points, roots, the user-profile root, the Vault root, source/destination overlap, and destination escape.
- Build under the exact item root in `.staging-*`, hash-readback every output, write the export manifest last, and leave the prior verified latest intact or recoverable on every failure.
- Treat source versions as immutable: identical re-export returns `already_exported`; different bytes for the same `v0.N` return `immutable_export_conflict`.
- Existing runtime schema version `1` remains compatible. `publicationRoot` is an optional non-secret path.
- Do not add DOCX, external blog posting, background timers, bulk history scanning, or desktop-to-Vault reverse synchronization.
- Do not commit or push during execution unless the user explicitly authorizes it.
- The Local REST bearer key visible in prior screenshots must never appear in code, fixtures, logs, manifests, or documentation. Key rotation through Obsidian `Reset all crypto` is a separate manual security action.

## File and Interface Map

### New files

- `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/export_publication_bundle.py` — profile detection, validation preflight, copy-ready derivation, link rewriting, safe naming, transaction/history handling, manifest creation, and static index regeneration.
- `tests/test_desktop_publication_export.py` — valid package, security, transaction, history, index, privacy, and CLI tests.
- `bootstrap/lib/PublicationLibrary.psm1` — known-folder root resolution, safe root initialization, managed usage file/index creation, and exact Vault-folder shortcut creation.
- `plugins/obsidian-manuscript-publisher/bootstrap/lib/PublicationLibrary.psm1` — byte-identical installable mirror.
- `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/publication-library.md` — user-visible bundle contract, commands, statuses, and recovery semantics.

### Modified files

- `bootstrap/lib/Environment.psm1` and mirrored plugin copy — optional `publicationRoot` runtime field with schema-v1 backward compatibility.
- `bootstrap/install-windows.ps1` and mirrored plugin copy — initialize the safe publication root after Vault/runtime setup.
- `bootstrap/doctor.ps1` and mirrored plugin copy — report publication-root and shortcut readiness without requiring an export.
- `tests/InstallerContract.Tests.ps1` — known-folder/runtime/shortcut/root-safety and mirror-equality contracts.
- `tests/SecretScan.Tests.ps1` — assert exported fixtures and publication manifests cannot include Local REST secret material.
- `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/SKILL.md` — run desktop export after successful render, independently report Vault publication and desktop export, and expose explicit re-export/backfill triggers.
- `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/agents/openai.yaml` — mention verified desktop publication bundles in the skill description/default prompt.
- `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/manuscript-schema.md` — document `book_a4` desktop bundle mapping.
- `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/blog-schema.md` — document `adaptive_blog` desktop bundle mapping and no-PDF rule.
- `tests/test_obsidian_manuscript_workspace.py` — script/reference/trigger/profile-isolation contract.
- `README.md` — beginner workflow for copy text, numbered images, preview, history, and explicit commands.

### Python interfaces

```python
@dataclass(frozen=True)
class ExportRequest:
    source_version_dir: Path
    publication_root: Path
    project_destination_root: str
    vault_path: Path | None = None

@dataclass(frozen=True)
class AssetExport:
    asset_id: str
    source_path: Path
    source_relative_path: str
    destination_relative_path: str
    insertion_label: str
    caption: str
    alt_text: str
    sha256: str

@dataclass(frozen=True)
class VerifiedPackage:
    profile: Literal["book_a4", "adaptive_blog"]
    source_version: str
    title: str
    item_parts: tuple[str, ...]
    metadata_path: Path
    markdown_path: Path
    html_path: Path
    pdf_path: Path | None
    validation_path: Path
    assets: tuple[AssetExport, ...]
    source_hashes: dict[str, str]
    vault_publication_status: str
```

The implementation exposes the exact call signatures `inspect_verified_package(request: ExportRequest) -> VerifiedPackage`, `build_bundle(package: VerifiedPackage, staging_dir: Path) -> dict`, `export_publication_bundle(request: ExportRequest) -> dict`, and `regenerate_root_index(publication_root: Path) -> Path`.

CLI contract:

```text
export_publication_bundle.py
  --source-version-dir <absolute v0.N folder>
  --publication-root <absolute selected publication root>
  --project-destination-root <registry destination_root>
  [--vault-path <absolute configured Vault path>]
```

Success JSON uses `status` equal to `exported`, `history_exported`, or `already_exported`; deterministic failures use an `ExportError.code`, including `validation_not_ready`, `stale_validation`, `unexpected_source_file`, `unsafe_path`, `asset_hash_mismatch`, and `immutable_export_conflict`.

### PowerShell interfaces

```powershell
Resolve-PublicationRoot [-PublicationRoot <path>] [-DesktopPath <test override>]
Initialize-PublicationLibrary -PublicationRoot <path> -VaultPath <path>
New-VaultFolderShortcut -PublicationRoot <path> -VaultPath <path> [-ShellFactory <scriptblock>]
Test-PublicationLibrary -PublicationRoot <path> -VaultPath <path>
```

---

### Task 1: Verified Package Preflight and Profile-Specific Bundles

**Files:**
- Create: `tests/test_desktop_publication_export.py`
- Create: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/export_publication_bundle.py`

**Interfaces:**
- Consumes: existing `validate_manuscript.validate_package`, `validate_blog.validate_package`, renderer contracts, `manuscript.json`, `blog.json`, `asset-manifest.json`, and profile validation reports.
- Produces: `ExportRequest`, `VerifiedPackage`, `ExportError`, `inspect_verified_package()`, `build_bundle()`, `export_publication_bundle()`.

- [ ] **Step 1: Add valid `book_a4` and `adaptive_blog` fixture builders**

Reuse `ManuscriptRendererTests.write_valid_package()` and `BlogPackageMixin.write_valid_package()`, then complete the immutable source package exactly as publication requires. The book helper must set `output_profile: book_a4`, `source_markdown`, write `production-plan.json`, validate, and render; the blog helper must validate and render.

```python
def make_book_version(root: Path, version="v0.1") -> Path:
    version_dir = root / version
    version_dir.mkdir(parents=True)
    manuscript, manifest, report = ManuscriptRendererTests().write_valid_package(version_dir)
    data = json.loads(manuscript.read_text(encoding="utf-8"))
    data.update(output_profile="book_a4", source_markdown="chapter.md")
    manuscript.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    (version_dir / "chapter.md").write_text("# 원고\n", encoding="utf-8")
    (version_dir / "production-plan.json").write_text(
        json.dumps({"status": "verified", "steps": ["Skill 구현"]}, ensure_ascii=False),
        encoding="utf-8",
    )
    run_validator_and_renderer(manuscript, manifest, report, version_dir)
    return version_dir
```

In the same test module, define `PublicationExportTestCase` with `setUp()` creating `source_root`, `publication_root`, and `vault_root` under one `TemporaryDirectory`. Define `book_request(version="v0.1")` and `blog_request(version="v0.1")` to call the fixture builders and return `ExportRequest` using `project_destination_root="AAA AI Agent Automation"`. Define `mutate_json(path, callback)`, `tree_hashes(root)`, `tampered_blog_request()`, `corrupt_exported_copy_without_touching_source(root)`, and `assert_export_fails_before_destination(asset_path, code)` in that base class; each helper performs only the exact mutation named and asserts the source package remains present.

- [ ] **Step 2: Write failing tests for exact output bundles**

```python
def test_book_exports_copy_text_markdown_html_pdf_guide_and_numbered_images(self):
    result = exporter.export_publication_bundle(self.book_request())
    latest = Path(result["latest_path"])
    self.assertEqual(result["status"], "exported")
    self.assertEqual(
        {p.relative_to(latest).as_posix() for p in latest.rglob("*") if p.is_file()},
        {
            "01 본문-복사용.txt", "02 원고.md", "03 미리보기.html",
            "04 인쇄용.pdf", "05 이미지-삽입순서.md",
            "images/01-미리보기.png", "images/02-Step-01.png",
            "images/03-실전-활용.png", "_meta/export-manifest.json",
        },
    )

def test_blog_exports_no_pdf_and_orders_hero_before_section_visuals(self):
    result = exporter.export_publication_bundle(self.blog_request())
    latest = Path(result["latest_path"])
    self.assertFalse(any(path.suffix.lower() == ".pdf" for path in latest.rglob("*")))
    guide = (latest / "04 이미지-삽입순서.md").read_text(encoding="utf-8")
    self.assertLess(guide.index("01-대표이미지.png"), guide.index("02-검증근거-1.png"))
```

- [ ] **Step 3: Run the focused tests and confirm RED**

Run:

```powershell
& $env:CODEX_BUNDLED_PYTHON -m unittest tests.test_desktop_publication_export -v
```

Expected: import/file failure because `export_publication_bundle.py` does not exist.

- [ ] **Step 4: Implement profile detection and fresh-validation preflight**

Implement these exact gates before creating a destination directory:

```python
def inspect_verified_package(request: ExportRequest) -> VerifiedPackage:
    source = reject_reparse_tree(request.source_version_dir.resolve())
    version = require_version_name(source.name)  # ^v0\.[1-9][0-9]*$
    if (source / "manuscript.json").is_file() == (source / "blog.json").is_file():
        raise ExportError("profile_ambiguous", "exactly one profile metadata file is required")
    return inspect_book(request, source, version) if (source / "manuscript.json").is_file() else inspect_blog(request, source, version)
```

For each profile, recompute metadata and manifest SHA-256 and compare them to `validated_inputs`; call the existing validator again; require exact rendered files; recompute every manifest asset hash; and reject every source file outside the profile allowlist except root `publication-validation.json`, which is read only for its status and is never copied. For blog, recompute expected Markdown/HTML with `render_blog`; for book, require the source Markdown, HTML, and PDF and reuse the existing fresh manuscript validator.

- [ ] **Step 5: Implement deterministic editorial image order and filenames**

Book order is `preview`, every Step in JSON order, then `real_world_use_visual`. Blog order is `hero_visual`, then each section visual in section order. Derive safe readable names with sequence prefixes and preserve `.png`, `.jpg`, or `.jpeg`:

```python
def ordered_visuals(metadata: dict, profile: str) -> list[tuple[str, dict]]:
    if profile == "book_a4":
        return [("미리보기", metadata["preview"]["visual"])] + [
            (f"Step-{index:02d}", step["visual"])
            for index, step in enumerate(metadata["steps"], 1)
        ] + [("실전-활용", metadata["real_world_use_visual"])]
    return [("대표이미지", metadata["hero_visual"])] + [
        (f"검증근거-{index}", section["visual"])
        for index, section in enumerate(metadata["sections"], 1)
        if section.get("visual") is not None
    ]
```

- [ ] **Step 6: Implement copy-ready text, Markdown/HTML rewriting, guide, and manifest**

Generate plain text from validated JSON, not by scraping PDF/HTML. Preserve paragraph boundaries and insert exactly one marker immediately where each visual appears:

```text
[이미지 02 삽입: 생성 결과 검증과 오류 수정]
캡션: 그림 1-03-2. 검증 결과와 수정 지점
```

For book text, preserve title → `[이번 챕터에서는]` → `[한눈에 보기]` → `[미리 보기]` → `[실습하기]` Step 1..N → `[실전 활용하기]` → `[꿀팁 더하기]` → caution. For blog text, preserve title/dek → hero marker → lead → each section/optional visual → next action → closing → tags.

Rewrite only manifest-listed image targets in Markdown and `<img src>` values. Book HTML maps each exact source `Path.as_uri()`; blog HTML maps version-relative asset paths. Fail if a publication document references an unlisted local image. Copy book PDF byte-for-byte.

- [ ] **Step 7: Run focused bundle tests and confirm GREEN**

Run:

```powershell
& $env:CODEX_BUNDLED_PYTHON -m unittest tests.test_desktop_publication_export.ValidBundleTests -v
```

Expected: all valid book/blog bundle, copy-text marker, link-resolution, image-order, PDF/no-PDF, guide, and manifest tests pass.

- [ ] **Step 8: Review gate**

Inspect `git diff --check` and the focused test output. If the user later authorizes commits, stage only the two Task 1 files and use `feat: add verified desktop publication bundles`.

### Task 2: Path Safety, Exact Allowlists, and Privacy

**Files:**
- Modify: `tests/test_desktop_publication_export.py`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/export_publication_bundle.py`
- Modify: `tests/SecretScan.Tests.ps1`

**Interfaces:**
- Consumes: Task 1 `inspect_verified_package()` and `build_bundle()`.
- Produces: `sanitize_component()`, `allocate_component()`, `assert_safe_publication_boundary()`, `reject_reparse_tree()`, and deterministic `ExportError.code` values.

- [ ] **Step 1: Add a parameterized RED security suite**

```python
def test_rejects_stale_validation_before_creating_publication_root(self):
    request = self.book_request()
    mutate_json(request.source_version_dir / "manuscript.json", lambda d: d.update(title="변조"))
    with self.assertRaisesRegex(exporter.ExportError, "stale_validation"):
        exporter.export_publication_bundle(request)
    self.assertFalse(request.publication_root.exists())

def test_rejects_adjacent_secret_and_never_copies_it(self):
    request = self.blog_request()
    (request.source_version_dir / "data.json").write_text('{"apiKey":"forbidden"}', encoding="utf-8")
    with self.assertRaisesRegex(exporter.ExportError, "unexpected_source_file"):
        exporter.export_publication_bundle(request)

def test_rejects_traversal_absolute_unc_and_reparse_asset_paths(self):
    for unsafe in ("../secret.png", "C:/secret.png", "//server/share/a.png", "assets/../a.png"):
        with self.subTest(unsafe=unsafe):
            self.assert_export_fails_before_destination(unsafe, "unsafe_path")
```

Also test missing render files, wrong asset bytes, root/user/Vault/source destinations, source inside destination, destination inside source, symlink/junction/reparse source entries, destination reparse ancestors, reserved names (`CON`, `AUX`, `COM1`, `LPT9`), trailing dots/spaces, duplicate sanitized names, and arbitrary HTML local-image references.

- [ ] **Step 2: Run the security tests and confirm RED**

Run:

```powershell
& $env:CODEX_BUNDLED_PYTHON -m unittest tests.test_desktop_publication_export.SecurityBoundaryTests -v
```

Expected: failures for unimplemented rejection codes and name allocation.

- [ ] **Step 3: Implement component sanitization with stable collision suffixes**

```python
WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}

def sanitize_component(raw: str) -> str:
    value = CONTROL_OR_FORBIDDEN.sub("_", unicodedata.normalize("NFC", raw)).rstrip(" .")
    if not value or value.upper() in WINDOWS_RESERVED:
        value = f"_{value or 'untitled'}"
    return value[:120].rstrip(" .")

def allocate_component(raw: str, used: set[str]) -> str:
    base = sanitize_component(raw)
    key = base.casefold()
    if key not in used:
        used.add(key)
        return base
    suffix = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]
    candidate = f"{base[:111]}--{suffix}"
    used.add(candidate.casefold())
    return candidate
```

- [ ] **Step 4: Implement boundary and reparse checks before writes**

Resolve all paths with `strict` checks where they must exist, compare using `os.path.normcase`, reject filesystem roots and the resolved user profile, and require every derived item/staging/latest/history path to satisfy `candidate.relative_to(publication_root)`. Inspect every existing source entry and destination ancestor with `os.lstat`; reject `stat.S_ISLNK` and `FILE_ATTRIBUTE_REPARSE_POINT`.

Before any recursive staging cleanup, assert the resolved target name starts with `.staging-` and its parent equals the exact resolved item root. Never call a recursive delete on the publication root, item root, `00 최신본`, or `99 이전버전`.

- [ ] **Step 5: Extend the secret scan contract**

Add static checks that source code and documentation do not contain a bearer token and that fixture manifests never use forbidden keys:

```powershell
$forbiddenPublicationKeys = 'apiKey|bearerToken|privateKey|certificateContents|restDataPath'
$publicationSources = Get-ChildItem -LiteralPath $repoRoot -Recurse -File |
    Where-Object { $_.Name -match 'publication|export' -and $_.Length -lt 1MB }
@($publicationSources | Select-String -Pattern 'Bearer\s+[0-9a-f]{32,}' -AllMatches).Count | Should Be 0
```

- [ ] **Step 6: Run security tests and confirm GREEN**

Run:

```powershell
& $env:CODEX_BUNDLED_PYTHON -m unittest tests.test_desktop_publication_export.SecurityBoundaryTests -v
Invoke-Pester -Script .\tests\SecretScan.Tests.ps1
```

Expected: all malicious-path, stale/hash, allowlist, and secret tests pass without creating/changing `00 최신본`.

- [ ] **Step 7: Review gate**

Run `git diff --check`. If explicitly authorized later, stage only Task 2 files and use `test: harden desktop publication export boundaries`.

### Task 3: Atomic Latest, Immutable History, Idempotency, and Recovery

**Files:**
- Modify: `tests/test_desktop_publication_export.py`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/export_publication_bundle.py`

**Interfaces:**
- Consumes: verified `build_bundle()` output and export manifest schema from Task 1.
- Produces: `verify_bundle()`, `recover_item_root()`, `promote_staging_bundle()`, and statuses `exported`, `history_exported`, `already_exported`, `immutable_export_conflict`.

- [ ] **Step 1: Add RED transaction-boundary tests**

Patch `os.replace` at each promotion boundary and preserve a byte snapshot of the previous latest:

```python
def test_failed_newer_export_preserves_previous_latest_bytes(self):
    first = exporter.export_publication_bundle(self.book_request(version="v0.1"))
    latest = Path(first["latest_path"])
    before = tree_hashes(latest)
    with mock.patch.object(exporter.os, "replace", side_effect=OSError("simulated swap failure")):
        with self.assertRaises(OSError):
            exporter.export_publication_bundle(self.book_request(version="v0.2"))
    exporter.recover_item_root(latest.parent)
    self.assertEqual(tree_hashes(latest), before)

def test_identical_same_version_is_idempotent_but_conflicting_bytes_are_rejected(self):
    request = self.book_request(version="v0.1")
    self.assertEqual(exporter.export_publication_bundle(request)["status"], "exported")
    self.assertEqual(exporter.export_publication_bundle(request)["status"], "already_exported")
    corrupt_exported_copy_without_touching_source(request.publication_root)
    with self.assertRaisesRegex(exporter.ExportError, "immutable_export_conflict"):
        exporter.export_publication_bundle(request)
```

Add cases for failure before staging completion, after staging verification, after old-latest archive, after new-latest promotion, and before index update. Assert the old latest is hash-identical or deterministically restored.

- [ ] **Step 2: Run transaction tests and confirm RED**

Run:

```powershell
& $env:CODEX_BUNDLED_PYTHON -m unittest tests.test_desktop_publication_export.TransactionTests -v
```

- [ ] **Step 3: Implement staged hash readback and immutable fingerprints**

Write all reader files first, calculate their hashes, then write `_meta/export-manifest.json` last through an fsynced temporary file and `os.replace`. `verify_bundle()` rereads every listed file, confirms exact relative paths and hashes, confirms no unlisted file, and calculates an immutable fingerprint from profile, project, source version, source hashes, image rename map, and exported-content hashes excluding `exported_at`.

- [ ] **Step 4: Implement version-aware promotion**

Use numeric `v0.N` ordering:

- no latest: promote selected version to `00 최신본`;
- selected version newer than latest: ensure the old version's history destination is absent or byte-identical, move old latest to `99 이전버전/<old-version>`, then promote staging;
- selected version older than latest: place it only at `99 이전버전/<selected-version>` and return `history_exported`;
- selected version equal and byte-identical: return `already_exported` without rewriting;
- selected version equal but different: raise `immutable_export_conflict`.

Never overwrite a non-identical history directory.

- [ ] **Step 5: Implement interrupted-export recovery**

`recover_item_root()` only inspects exact children matching `.staging-*` and `.previous-*`. It validates their manifests before action. If latest is absent and one verified `.previous-*` exists, restore it. If latest is verified, archive a verified previous bundle under its manifest version. Remove only verified exporter-owned staging directories whose resolved parent is the exact item root; reject ambiguous multiple previous bundles for manual review.

- [ ] **Step 6: Run transaction tests and confirm GREEN**

Run:

```powershell
& $env:CODEX_BUNDLED_PYTHON -m unittest tests.test_desktop_publication_export.TransactionTests -v
```

Expected: every injected boundary failure retains or restores the prior latest; immutable/idempotent/history statuses are exact.

- [ ] **Step 7: Review gate**

Run `git diff --check`. If explicitly authorized later, stage Task 3 files and use `feat: add recoverable publication history transactions`.

### Task 4: Static Root Index and Beginner Usage Surface

**Files:**
- Modify: `tests/test_desktop_publication_export.py`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/scripts/export_publication_bundle.py`

**Interfaces:**
- Consumes: verified latest manifests created by Task 3.
- Produces: `regenerate_root_index(publication_root)`, `00 원고 목록.html`, and `00 사용 방법.txt`.

- [ ] **Step 1: Add RED index tests**

```python
def test_index_groups_project_and_profile_with_offline_relative_links(self):
    exporter.export_publication_bundle(self.book_request())
    exporter.export_publication_bundle(self.blog_request())
    page = (self.publication_root / "00 원고 목록.html").read_text(encoding="utf-8")
    self.assertIn("AAA AI Agent Automation", page)
    self.assertIn("출판 원고형", page)
    self.assertIn("범용 블로그형", page)
    self.assertIn("01%20본문-복사용.txt", page)
    self.assertNotIn("<script", page.lower())
    self.assertNotRegex(page, r"https?://")

def test_failed_item_export_does_not_change_index(self):
    exporter.export_publication_bundle(self.book_request())
    before = (self.publication_root / "00 원고 목록.html").read_bytes()
    with self.assertRaises(exporter.ExportError):
        exporter.export_publication_bundle(self.tampered_blog_request())
    self.assertEqual((self.publication_root / "00 원고 목록.html").read_bytes(), before)
```

- [ ] **Step 2: Run index tests and confirm RED**

Run:

```powershell
& $env:CODEX_BUNDLED_PYTHON -m unittest tests.test_desktop_publication_export.IndexTests -v
```

- [ ] **Step 3: Implement static manifest-only index regeneration**

Scan only exact `00 최신본/_meta/export-manifest.json` locations beneath non-reparse project/profile/item directories. Validate each bundle before indexing. Escape every visible field with `html.escape`, URL-encode relative link components with `urllib.parse.quote`, include PDF only for book, and emit no JavaScript, tracking, remote URL, inline event handler, or source absolute path. Write to `.00-index.tmp`, fsync, and `os.replace` only after item promotion succeeds.

- [ ] **Step 4: Implement the managed usage file**

Write UTF-8 text with this exact workflow and a managed header:

```text
[Codex Obsidian Manuscript - managed publication guide]
1. 각 원고의 00 최신본에서 01 본문-복사용.txt를 열어 글을 복사합니다.
2. 이미지-삽입순서.md를 보며 images 폴더의 번호순 이미지를 업로드합니다.
3. 03 미리보기.html과 책 원고의 04 인쇄용.pdf는 화면·인쇄 확인에 사용합니다.
옵시디언 보관함은 원본 기록이며, 바탕화면 출판함은 검증된 복사용 결과입니다.
```

Only replace an existing usage file when it contains the managed header; otherwise fail without overwriting user content.

- [ ] **Step 5: Run index tests and confirm GREEN**

Run:

```powershell
& $env:CODEX_BUNDLED_PYTHON -m unittest tests.test_desktop_publication_export.IndexTests -v
```

- [ ] **Step 6: Review gate**

If explicitly authorized later, stage Task 4 files and use `feat: add offline publication library index`.

### Task 5: Windows Known-Folder Root, Runtime Compatibility, and Vault Shortcut

**Files:**
- Create: `bootstrap/lib/PublicationLibrary.psm1`
- Create: `plugins/obsidian-manuscript-publisher/bootstrap/lib/PublicationLibrary.psm1`
- Modify: `bootstrap/lib/Environment.psm1`
- Modify: `plugins/obsidian-manuscript-publisher/bootstrap/lib/Environment.psm1`
- Modify: `bootstrap/install-windows.ps1`
- Modify: `plugins/obsidian-manuscript-publisher/bootstrap/install-windows.ps1`
- Modify: `bootstrap/doctor.ps1`
- Modify: `plugins/obsidian-manuscript-publisher/bootstrap/doctor.ps1`
- Modify: `tests/InstallerContract.Tests.ps1`

**Interfaces:**
- Consumes: existing `Resolve-InstallPaths`, `Save-RuntimeConfig`, `Get-RuntimeConfig`, and configured Vault path.
- Produces: PowerShell interfaces listed in the File and Interface Map and optional runtime `publicationRoot`.

- [ ] **Step 1: Add RED Pester tests for known-folder resolution and schema-v1 compatibility**

```powershell
It "resolves the default publication root below the Windows Desktop known folder" {
    Import-Module $publicationModule -Force
    $desktop = Join-Path $TestDrive "Redirected Desktop"
    Resolve-PublicationRoot -DesktopPath $desktop | Should Be (Join-Path $desktop "옵시디언 원고")
}

It "loads a legacy schema-v1 runtime without publicationRoot" {
    Set-Content $configPath '{"schemaVersion":1,"vaultPath":"C:\\Vault","restDataPath":"C:\\Vault\\.obsidian\\plugins\\obsidian-local-rest-api\\data.json"}'
    $loaded = Get-RuntimeConfig -RuntimeConfigPath $configPath
    [string]::IsNullOrWhiteSpace([string]$loaded.publicationRoot) | Should Be $true
}
```

Add tests that runtime files contain no token/key, roots/drives/user-profile/Vault targets are rejected, existing unmanaged `00 사용 방법.txt` and `.lnk` are not overwritten, and the shortcut target is `explorer.exe` with the exact configured Vault as its argument. Inject a fake `ShellFactory` object so tests do not launch Explorer.

- [ ] **Step 2: Run Pester and confirm RED**

Run:

```powershell
Invoke-Pester -Script .\tests\InstallerContract.Tests.ps1
```

Expected: missing publication module/functions and mirror-list failure.

- [ ] **Step 3: Implement `PublicationLibrary.psm1`**

Resolve the default desktop with:

```powershell
$desktop = if ($DesktopPath) {
    [IO.Path]::GetFullPath($DesktopPath)
} else {
    [Environment]::GetFolderPath([Environment+SpecialFolder]::DesktopDirectory)
}
```

Validate publication root boundaries and reparse attributes before creating it. Create only the root and managed root files; never enumerate/copy Vault content. Build `00 Obsidian 보관함 폴더.lnk` with `WScript.Shell.CreateShortcut`, target `$env:WINDIR\explorer.exe`, quoted argument equal to the full Vault path, and working directory equal to the Vault parent. Refuse to replace an existing unmanaged shortcut.

- [ ] **Step 4: Extend runtime config without breaking schema version 1**

`Resolve-InstallPaths` returns `PublicationRoot`. `Save-RuntimeConfig` writes it as a normalized optional path. `Get-RuntimeConfig` accepts both old and new schema-v1 files, validates a present path, and returns it. It must continue validating `restDataPath` beneath the exact Vault plugin directory and must not read or write the API key.

- [ ] **Step 5: Integrate installer and doctor**

After safe Vault and runtime initialization, call `Initialize-PublicationLibrary`. Add `PublicationRoot` to installer output. Doctor calls `Test-PublicationLibrary` and reports independent fields:

```powershell
[pscustomobject]@{
    Status = $health.Status
    VaultPath = $runtime.vaultPath
    PublicationRoot = $publication.Root
    PublicationLibraryStatus = $publication.Status
    VaultShortcutStatus = $publication.ShortcutStatus
}
```

Local REST failure must not cause the doctor to delete or rebuild the publication root.

- [ ] **Step 6: Mirror bootstrap files and enforce byte equality**

Copy the final root bootstrap files into the installable plugin mirror only after the root versions pass tests. Add `lib\PublicationLibrary.psm1` to the exact mirror hash list in `InstallerContract.Tests.ps1`.

- [ ] **Step 7: Run Pester and confirm GREEN**

Run:

```powershell
Invoke-Pester -Script .\tests\InstallerContract.Tests.ps1
Invoke-Pester -Script .\tests\SecretScan.Tests.ps1
```

- [ ] **Step 8: Review gate**

If explicitly authorized later, stage only Task 5 files and use `feat: initialize Windows desktop publication library`.

### Task 6: Skill Workflow, Schemas, and Beginner Documentation

**Files:**
- Create: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/publication-library.md`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/SKILL.md`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/agents/openai.yaml`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/manuscript-schema.md`
- Modify: `plugins/obsidian-manuscript-publisher/skills/obsidian-manuscript-publisher/references/blog-schema.md`
- Modify: `tests/test_obsidian_manuscript_workspace.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: exporter CLI and PowerShell/runtime interfaces from Tasks 1–5.
- Produces: deterministic natural-language routing and accurate completion reporting.

- [ ] **Step 1: Add RED workspace-contract tests**

```python
def test_skill_exports_only_after_ready_validation_and_render(self):
    skill = SKILL_PATH.read_text(encoding="utf-8")
    self.assertIn("export_publication_bundle.py", skill)
    self.assertLess(skill.index("status: ready"), skill.index("export_publication_bundle.py"))

def test_skill_reports_vault_and_desktop_outcomes_separately(self):
    skill = SKILL_PATH.read_text(encoding="utf-8")
    self.assertIn("vault_publication_status", skill)
    self.assertIn("desktop_export_status", skill)

def test_blog_contract_forbids_desktop_pdf(self):
    schema = BLOG_SCHEMA.read_text(encoding="utf-8")
    self.assertIn("adaptive_blog desktop bundle never contains a PDF", schema)
```

Also assert explicit triggers for `바탕화면 출판함만 다시 만들어줘` and explicitly named backfill, and assert no trigger authorizes implicit historical scanning.

- [ ] **Step 2: Run workspace tests and confirm RED**

Run:

```powershell
& $env:CODEX_BUNDLED_PYTHON -m unittest tests.test_obsidian_manuscript_workspace -v
```

- [ ] **Step 3: Add the publication-library reference contract**

Document exact folder/file names, copy workflow, manifest fields, statuses, commands, security exclusions, latest/history behavior, and recovery. Include these command routes:

```text
원고로 완성해줘
범용 블로그형으로 만들어줘
바탕화면 출판함만 다시 만들어줘
v0.3 검증본을 출판함에 정리해줘
```

The last route must require an exact project/profile/version; it must not scan all old versions.

- [ ] **Step 4: Integrate export after each independent profile pipeline**

For both profiles, the workflow order is validate → render → attempt Vault publication when available → desktop export. A Vault REST failure does not invalidate a fresh local package and does not block desktop export; report the outcomes separately. A validation/render/export failure never claims completion and never changes the prior desktop latest.

Pass the registry `destination_root` exactly as `--project-destination-root`; obtain `publicationRoot` and Vault path from runtime config; never infer the project folder from title and never pass credentials to the exporter.

- [ ] **Step 5: Update schemas and README**

Explain that `01 본문-복사용.txt` is the primary paste source, numbered images are uploaded using the guide, HTML/PDF are previews, the Vault remains the source of record, and `99 이전버전` is immutable. State that no direct Naver/Tistory/WordPress posting occurs.

Add a security warning without reproducing any secret: if a Local REST key was exposed, use Obsidian `Reset all crypto`; `Re-generate certificates` alone does not rotate the API key.

- [ ] **Step 6: Run workspace tests and confirm GREEN**

Run:

```powershell
& $env:CODEX_BUNDLED_PYTHON -m unittest tests.test_obsidian_manuscript_workspace -v
```

- [ ] **Step 7: Review gate**

If explicitly authorized later, stage only Task 6 files and use `docs: integrate verified desktop publication workflow`.

### Task 7: Full Regression, Live Smoke Export, and Manual Acceptance

**Files:**
- Modify only if validation exposes a defect in files already listed in Tasks 1–6.
- Produce local smoke output outside Git: `<workspace>\publish\desktop-publication-smoke\` first, then the real configured publication root only after all automated checks pass.

**Interfaces:**
- Consumes: complete exporter, bootstrap module, skill/docs, and existing verified sample `<workspace>\publish\adaptive-blog-verification-v0.1`.
- Produces: evidence that the feature works without weakening existing manuscript, blog, REST, installer, or privacy contracts.

- [ ] **Step 1: Load the bundled Python runtime and run the full Python suite**

Use `codex_app__load_workspace_dependencies` to resolve Python, set `CODEX_BUNDLED_PYTHON`, then run:

```powershell
& $env:CODEX_BUNDLED_PYTHON -m unittest discover -s tests -p "test_*.py" -v
```

Expected: every prior test plus `test_desktop_publication_export.py` passes. Record the exact count; do not reuse the earlier 126-test count as a claim.

- [ ] **Step 2: Run installer and privacy regression suites**

```powershell
Invoke-Pester -Script .\tests\InstallerContract.Tests.ps1
Invoke-Pester -Script .\tests\SecretScan.Tests.ps1
```

Expected: all contracts pass, including byte-identical bootstrap mirrors and no secret/path leakage.

- [ ] **Step 3: Run a workspace-only smoke export**

```powershell
& $env:CODEX_BUNDLED_PYTHON `
  .\plugins\obsidian-manuscript-publisher\skills\obsidian-manuscript-publisher\scripts\export_publication_bundle.py `
  --source-version-dir "<workspace>\publish\adaptive-blog-verification-v0.1" `
  --publication-root "<workspace>\publish\desktop-publication-smoke" `
  --project-destination-root "AAA AI Agent Automation" `
  --vault-path "%USERPROFILE%\Documents\Codex-Wiki"
```

Expected JSON: `status: exported`, `profile: adaptive_blog`, and no PDF. Open/check `01 본문-복사용.txt`, all rewritten links, two numbered landscape images, static index, and manifest hashes. Scan the smoke root for `apiKey`, `Bearer`, certificate/private-key markers, source attachment paths, and conversation text not present in the public article.

- [ ] **Step 4: Exercise idempotency and failure preservation in smoke output**

Run the same command again and require `already_exported`. Then run against a copied fixture with one changed asset byte and require failure while hashes of the prior `00 최신본` remain unchanged.

- [ ] **Step 5: Initialize and test the real desktop root**

Only after Steps 1–4 pass, call the PowerShell module with the runtime-configured paths. Confirm:

- `<Desktop>\옵시디언 원고` exists;
- `00 Obsidian 보관함 폴더.lnk` opens the exact configured Vault folder in Explorer and never uses `obsidian://`;
- `00 원고 목록.html` opens offline;
- `01 본문-복사용.txt` is cleanly selectable/copyable;
- every guide row maps to one numbered image;
- the current verified blog preview renders with local images;
- no prior Vault content was moved or altered.

- [ ] **Step 6: Rotate the exposed Local REST key manually**

In Obsidian Local REST API settings, press `Reset all crypto`, then rerun `bootstrap\doctor.ps1`. Do not record the new key. This security action is independent of desktop export acceptance.

- [ ] **Step 7: Run completion checks**

```powershell
git diff --check
git status --short
```

Review that only intended repository files changed, generated smoke/desktop artifacts are untracked outside the repository, and no commit/push occurred without explicit user authorization.

- [ ] **Step 8: Final report**

Report exact test counts and Pester results, the real publication-root path, exported profile/version/status, copy-text and preview locations, shortcut result, Vault publication status separately, and any manual action still required. Never claim desktop export means Vault REST publication succeeded.

## Self-Review Checklist

- [ ] Every design acceptance item maps to Tasks 1–7.
- [ ] Both profiles have independent output contracts and only book has PDF.
- [ ] Copy-ready text comes from validated structured JSON and includes image markers.
- [ ] Link rewriting is restricted to manifest-listed assets.
- [ ] Exact allowlists, fresh validation, asset hashes, reparse/path boundaries, secret exclusion, and no-source-overlap are tested before writes.
- [ ] Latest/history promotion is idempotent, immutable, version-aware, and recoverable at each failure boundary.
- [ ] Index update occurs only after item success and contains no script/tracking/remote URL.
- [ ] Known-folder and runtime behavior works for old and new schema-v1 configurations.
- [ ] Shortcut opens the exact folder through Explorer, not an Obsidian URI.
- [ ] Vault and desktop statuses are reported separately.
- [ ] No placeholder language (`TBD`, `TODO`, `implement later`, `similar to`) remains.
- [ ] No commit or push is performed without explicit user authorization.
