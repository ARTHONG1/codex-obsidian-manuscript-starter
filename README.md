# Codex Obsidian Manuscript Starter

Codex 대화를 Obsidian에 대화별로 저장하고, 모아 둔 재료로 **블로그 글**이나 **내가 등록한 양식의 원고**를 만드는 도구입니다.

**Windows 10/11에서 Codex만 설치되어 있으면 시작할 수 있습니다.** 아래 요청문을 Codex에 붙여 넣으세요. Obsidian 설치, 새 보관함 생성, 연결과 스킬 설치를 안내합니다. 설치 동의와 필요한 재시작은 사용자가 진행하며, 소요 시간은 PC와 다운로드 환경에 따라 달라집니다.

## 처음 설치하기

아래 내용을 통째로 복사해 **Codex 채팅창**에 입력하세요.

```text
GitHub의 ARTHONG1/codex-obsidian-manuscript-starter v0.7.1 릴리스를 처음부터 설치해줘.
나는 Codex만 설치한 초보자야. Obsidian 설치, 새 빈 보관함 생성, Local REST API 연결, 스킬 설치와 연결 확인까지 진행해줘.
고정 버전의 릴리스 파일과 체크섬을 검증한 뒤 설치하고, 기존 보관함과 설정은 보존해줘.
API 키와 인증서 값은 출력하지 마. 설치 동의가 필요하면 먼저 설명해줘.
Codex 또는 Obsidian 재시작이 필요하면 재시작 후 입력할 문장도 알려줘.
doctor 왕복 검증이 ready가 될 때까지 설치 완료라고 말하지 마.
```

Codex가 설치 동의를 요청하면 내용을 확인하고 답하세요. Obsidian이 열리면 켜 둔 채 안내를 따르면 됩니다. 도중에 앱을 재시작했다면 다음 한 문장으로 이어 갑니다.

설치는 전용 새 빈 폴더에 보관함을 만듭니다. 이미 쓰고 있는 Obsidian 보관함을 그대로 연결하는 기능은 아직 없습니다. 기존 파일이 있는 폴더는 절대 덮어쓰지 않습니다.

```text
중단된 Codex Obsidian Manuscript Starter 설치를 이어서 진행해줘.
```

연결에 성공했는지는 임시 메모를 만들고, 읽고, 지우는 실제 점검으로 확인합니다. 자세한 안내는 [설치 가이드](docs/INSTALL_GUIDE.md), 전체 요청문은 [INSTALL_PROMPT.md](INSTALL_PROMPT.md)에 있습니다.

## 설치 후 이렇게 사용하세요

### 대화를 저장하기

```text
이 프로젝트를 원고 프로젝트로 등록해줘.
이 대화 전체를 옵시디언 원고 재료로 저장해줘.
```

대화 원본과 정리된 재료 카드가 대화 ID별 폴더에 저장됩니다. 대화를 더 나눴다면 `이 대화 원고 재료 최신화해줘`라고 요청하세요.

### 블로그 만들기

```text
이 대화 재료로 플랫폼 독립 범용 블로그형을 만들어줘.
```

범용 블로그형 (`adaptive_blog`)은 `blog.md`, `blog.html`과 이미지를 만듭니다. 내용을 복사해 네이버·티스토리·워드프레스에 옮겨 사용할 수 있습니다. 네이버·티스토리·워드프레스에 자동 게시하지 않습니다.

### 내 양식으로 원고 만들기

PDF·DOCX·이미지 예시를 Codex에 첨부하고 요청하세요.

```text
이 PDF를 분석해서 ‘내 원고 양식’ 템플릿 후보를 만들어줘.
```

미리보기와 확인이 필요한 항목을 먼저 보여줍니다. 마음에 들면 Codex가 표시한 **후보 ID를 그대로 넣어** 승인합니다.

```text
후보 ID <표시된 ID>를 승인하고 ‘내 원고 양식’으로 등록해줘.
이 대화 재료로 ‘내 원고 양식’ 원고를 만들어줘.
```

사용자 양식 (`custom_manuscript`)은 승인한 양식에 맞는 Markdown·HTML·PDF를 만듭니다. **기본 제공 고정 원고형은 v0.7.0부터 제거했습니다.** 기존에 저장한 원고와 대화는 지우지 않습니다. 새 원고를 요청할 때는 등록할 양식 또는 사용할 템플릿을 지정하세요.

### 필요한 대화만 삭제하기

```text
이 대화의 옵시디언 자료 묶음만 삭제해줘.
```

현재 대화 ID에 연결된 묶음이 대상입니다. Codex가 안내하는 삭제 범위를 확인하세요.

## 만든 파일은 어디에 있나요?

기본 출판함은 `<Windows 바탕화면>\옵시디언 원고`입니다. 블로그는 다음처럼 정리됩니다.

```text
옵시디언 원고\
├─ 00 원고 목록.html
└─ <프로젝트>\02 범용 블로그형\<주제>\
   ├─ 00 최신본\
   │  ├─ 01 본문-복사용.txt
   │  ├─ 02 블로그.md
   │  ├─ 03 미리보기.html
   │  ├─ 04 이미지-삽입순서.md
   │  └─ images\
   └─ 99 이전버전\
```

`01 본문-복사용.txt`에서 글을 복사하고, `이미지-삽입순서.md`의 안내에 맞춰 `images`의 이미지를 올리면 됩니다. 사용자 양식은 완료 메시지에 표시된 출력 폴더에서 Markdown·HTML·PDF를 열 수 있습니다. Obsidian 저장과 바탕화면 내보내기 결과는 각각 확인합니다.

## 막혔을 때

| 상황 | Codex에 입력할 말 |
| --- | --- |
| Obsidian 연결이 안 됨 / `Local REST API did not become ready` | Obsidian을 켜 두고 “옵시디언 연결 상태를 점검해줘.” |
| 설치 도중 종료·재시작함 | “중단된 설치를 이어서 진행해줘.” |
| 보관함이 비어 있지 않다고 함 | “기존 폴더는 보존하고 새 빈 보관함으로 설치해줘.” |
| 원고에 사용할 양식이 없다고 함 | 예시 파일을 첨부하고 “이 파일로 사용자 양식 후보를 만들어줘.” |

API 키가 노출됐다면 Obsidian 플러그인 설정의 `Reset all crypto`로 재발급합니다. `Re-generate certificates`는 인증서만 바꾸며 API 키는 바꾸지 않습니다. [자세한 문제 해결](docs/TROUBLESHOOTING.md)

## 제작자와 라이선스

**AI찬우쌤**이 만든 프로젝트입니다. [클래스똑딱](https://classddok.com/)도 함께 만나 보세요.

OpenAI·Codex·Obsidian의 공식 제품이 아니며 제휴·보증 관계가 없습니다. [MIT License](LICENSE) · [타사 라이선스 고지](THIRD_PARTY_NOTICES.md) · [보안 정책](SECURITY.md)

<details>
<summary>개발자용 검증 명령</summary>

Python 3.12 실행 경로를 `$Python312`에 지정한 뒤 실행합니다.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\ci\run-python-tests.ps1 -PythonPath $Python312
.\ci\run-pester-tests.ps1 -Path .\tests\InstallerContract.Tests.ps1,.\tests\PythonRuntimeContract.Tests.ps1,.\tests\SecretScan.Tests.ps1 -ExpectedSkipCount 0
.\ci\run-all-tests.ps1 -PythonPath $Python312 -ExpectedPythonSkipCount 3
.\ci\build-release.ps1 -SourceRoot . -OutputRoot .\artifacts\release -Version 0.7.1
.\ci\verify-release.ps1 -Archive .\artifacts\release\codex-obsidian-manuscript-starter-v0.7.1.zip -Checksums .\artifacts\release\SHA256SUMS -TestRoot (Join-Path $env:TEMP ("release-install-" + [guid]::NewGuid().ToString("N")))
```

</details>

