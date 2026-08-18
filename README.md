# Codex Obsidian Manuscript Starter

Codex 대화를 Obsidian에 대화별로 분리해 보관하고, 검증된 재료를 바탕으로 **A4 세로형 한국어 출판 원고** 및 **플랫폼 독립 블로그 글**을 만들어 주는 Codex 플러그인입니다.

Windows 10/11과 Codex 데스크톱 앱/CLI 환경을 지원합니다. 사용자는 **Codex만 설치되어 있으면**, Obsidian 설치부터 보관함 생성, Local REST API 보안 연결, 스킬 설치까지 Codex가 원클릭으로 안내합니다.

---

## 핵심 기능

- **대화별 분리 아카이빙**: Codex 대화 ID별로 폴더를 생성하여 대화 원본과 원고 재료 카드를 안전하게 보관합니다.
- **출판 원고형 (`book_a4`)**: A4 세로형 인쇄용 PDF, 미리보기 HTML, Markdown 원고를 고품질 삽화와 함께 생성합니다.
- **범용 블로그형 (`adaptive_blog`)**: 네이버·티스토리·워드프레스 등에 복사해 바로 발행할 수 있는 `blog.md` 및 `blog.html`을 생성합니다. (사람이 쓴 글처럼 속이거나 AI 탐지기 회피를 보장하지 않으며, 정직하고 투명한 글쓰기를 지향합니다.)
- **사용자 맞춤 템플릿 (`custom_manuscript`)**: PDF·DOCX·이미지 샘플을 분석하여 원하는 출판사/기관 양식 후보를 만들고 승인 후 불변 템플릿으로 등록합니다.
- **바탕화면 출판함 원클릭 내보내기**: 완성된 원고와 이미지를 바탕화면에 복사하기 쉬운 번들로 자동 정돈합니다.
- **철저한 데이터 보호**: 개별 대화 삭제 요청 시 해당 대화 묶음만 안전하게 삭제하며, 기존 보관함이나 타 대화는 절대 훼손하지 않습니다.

---

## 3분 빠른 시작 (초보자용)

Codex 채팅창에 아래 문장을 그대로 입력하면 모든 준비가 완료됩니다.

```text
GitHub의 ARTHONG1/codex-obsidian-manuscript-starter 최신 안정 릴리스(v0.6.0)를 처음부터 설치해줘.
나는 Codex만 설치한 초보자야. Obsidian 설치, 새 빈 보관함 생성, Local REST API 연결, 원고 스킬 설치와 연결 확인까지 진행해줘.
기존 Obsidian 보관함과 기존 설정은 건드리지 말고, API 키와 인증서 값은 출력하지 마.
설치나 커뮤니티 플러그인 동의가 필요하면 먼저 나에게 물어봐.
Codex 또는 Obsidian 재시작이 필요하면 재시작 후 입력할 문장도 알려줘.
doctor 왕복 검증이 ready가 될 때까지 설치 완료라고 말하지 마.
```

> **수동 설치가 필요한 경우:**
> ```powershell
> codex plugin marketplace add ARTHONG1/codex-obsidian-manuscript-starter
> codex plugin add obsidian-manuscript-publisher@codex-obsidian-starter
> ```

설치 후 Obsidian이 열리면 연결 상태를 점검합니다.
```text
옵시디언 연결 상태를 점검해줘.
```

---

## 바로 쓰는 핵심 명령어

### 1. 대화 저장 및 재료화
```text
이 프로젝트를 원고 프로젝트로 등록해줘.
이 대화 전체를 옵시디언 원고 재료로 저장해줘.
```

### 2. 원고 및 블로그 생성
```text
이 프로젝트의 지정한 대화 재료만 바탕으로 Part 1-01 원고를 만들어줘.
이 대화 재료로 플랫폼 독립 범용 블로그형을 만들어줘.
검증 완료 원고 출판함으로 만들어줘.
```

### 3. 사용자 양식(템플릿) 등록 및 사용
```text
이 PDF를 분석해서 ‘출판사 A 원고형’ 템플릿 후보를 만들어줘.
현재 활성 후보를 승인하고 ‘출판사 A 원고형’ 템플릿으로 등록해줘.
이 대화 재료로 ‘출판사 A 원고형’ 원고를 만들어줘.
```

### 4. 대화 정리
```text
이 대화의 옵시디언 자료 묶음만 삭제해줘.
```

---

## 검증 완료 원고 출판함 구조

발행된 원고는 `<Windows 바탕화면>\옵시디언 원고` 폴더에 즉시 사용 가능한 형태로 정리됩니다.

```text
<Windows 바탕화면>\옵시디언 원고\
├─ 00 원고 목록.html
├─ 00 사용 방법.txt
└─ <프로젝트>\
   ├─ 01 출판 원고형\...\00 최신본\
   │  ├─ 01 본문-복사용.txt
   │  ├─ 02 원고.md
   │  ├─ 03 미리보기.html
   │  ├─ 04 인쇄용.pdf
   │  ├─ 05 이미지-삽입순서.md
   │  └─ images\
   └─ 02 범용 블로그형\...\00 최신본\
      ├─ 01 본문-복사용.txt
      ├─ 02 블로그.md
      ├─ 03 미리보기.html
      ├─ 04 이미지-삽입순서.md
      └─ images\
```

- `01 본문-복사용.txt`에서 본문을 복사하고, `images` 폴더의 번호에 맞춰 이미지를 첨부합니다.
- 새 버전이 생성되면 이전 결과물은 `99 이전버전\v0.N`에 안전하게 보존됩니다.
- 본 도구는 네이버·티스토리·워드프레스에 자동 게시하지 않습니다.

---

## 보안 및 데이터 보호 원칙

- **로컬 루프백 전용**: Obsidian Local REST API는 `https://127.0.0.1`에서만 통신하며 외부 네트워크로 노출하지 않습니다.
- **비파괴 설치**: 사용자의 기존 보관함 및 설정 파일은 덮어쓰거나 삭제하지 않습니다.
- **검증 완료 후 반영**: `validate_manuscript.py` 및 `validate_blog.py`를 통한 무결성 검증을 통과한 산출물만 안전하게 저장합니다.
- **인증 보안**: API 키가 화면에 노출되었을 경우 Obsidian 설정의 `Reset all crypto`로 재발급합니다. (`Re-generate certificates`는 인증서만 갱신하며 API 키를 변경하지 않습니다.)

---

## 문제 해결 가이드

| 증상 | 해결 방법 |
| :--- | :--- |
| **`Local REST API did not become ready`** | Obsidian을 켜둔 상태에서 `옵시디언 연결 상태를 점검해줘`를 다시 입력합니다. |
| **보관함이 비어 있지 않다는 오류** | 기존 파일을 삭제하지 말고, 새로운 빈 폴더를 지정합니다. |
| **설치 중 재시작 후 이어하기** | `중단된 Codex Obsidian Manuscript Starter 설치를 이어서 진행해줘.`를 입력합니다. |
| **플러그인 설정 및 연결 해제** | `bootstrap\uninstall.ps1`을 실행하면 연결 정보만 안전하게 초기화됩니다. |

---

## 개발 및 테스트

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\ci\run-python-tests.ps1 -PythonPath $Python312
.\ci\run-pester-tests.ps1 -Path .\tests\InstallerContract.Tests.ps1,.\tests\PythonRuntimeContract.Tests.ps1,.\tests\SecretScan.Tests.ps1 -ExpectedSkipCount 0
.\ci\run-all-tests.ps1 -PythonPath $Python312 -ExpectedPythonSkipCount 4
.\ci\build-release.ps1 -SourceRoot . -OutputRoot .\artifacts\release -Version 0.6.0
.\ci\verify-release.ps1 -Archive .\artifacts\release\codex-obsidian-manuscript-starter-v0.6.0.zip -Checksums .\artifacts\release\SHA256SUMS -TestRoot (Join-Path $env:TEMP ("release-install-" + [guid]::NewGuid().ToString("N")))
```

---

## 저작권 및 안내

- 이 프로젝트는 **AI찬우쌤**이 개발하였으며, [클래스똑딱](https://classddok.com/)의 교육 자동화 사례와 함께 제공됩니다.
- 본 프로젝트는 OpenAI, Codex, Obsidian의 공식 제품이 아니며 제휴나 보증 관계가 아닙니다.
- 라이선스: [MIT License](LICENSE) · [타사 고지](THIRD_PARTY_NOTICES.md) · [보안 정책](SECURITY.md)

