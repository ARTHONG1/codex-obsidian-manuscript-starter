# Codex Obsidian Manuscript Starter

Codex만 설치한 Windows 사용자도 Obsidian을 설치하고 연결한 뒤, Codex 대화를 대화별로 보관하고 출판용 원고로 만들 수 있게 안내하는 플러그인입니다.

이 프로젝트는 AI찬우쌤이 만들고 클래스똑딱의 교육 자동화 사례와 함께 소개합니다.

## 가장 먼저: 설치하는 방법

### 준비물

- Windows 10 또는 Windows 11
- Codex 데스크톱 앱 또는 Codex CLI
- **전용 새 빈 폴더**에 만들 Obsidian 보관함

Obsidian, Python, Pillow, ReportLab이 아직 없어도 됩니다. 설치 과정에서 확인하고 필요한 공식 설치 경로를 안내합니다.

이미 쓰고 있는 Obsidian 보관함을 그대로 연결하는 기능은 아직 없습니다. 기존 파일이 있는 폴더는 절대 덮어쓰지 않습니다.

### 방법 A — Codex에 한 번 붙여넣기

아래 파일을 열고 전체 내용을 복사해 Codex에 붙여넣습니다.

➡️ [Codex 초보자 설치 프롬프트](INSTALL_PROMPT.md)

또는 아래 문장을 그대로 복사합니다.

```text
이 저장소의 v0.3.1 기준으로 Codex Obsidian Manuscript Starter를 Windows에 처음부터 설치해줘.

나는 Codex만 설치한 초보자다. 다음 원칙을 지켜줘.
1. 공식 GitHub 저장소 ARTHONG1/codex-obsidian-manuscript-starter의 고정 release ref만 사용해줘.
2. Obsidian이 없으면 공식 Obsidian 설치 방법을 안내하거나 WinGet이 있을 때만 공식 패키지로 설치해줘.
3. Python이 없거나 Pillow==11.3.0, reportlab==4.4.3이 없으면 공식 Python 경로를 안내하고 같은 설치를 다시 실행할 수 있게 해줘.
4. 기존 Obsidian 보관함이나 기존 Local REST 설정은 건드리지 말고 새 빈 보관함을 사용해줘.
5. Local REST API는 127.0.0.1 HTTPS 전용으로 설정하고 API 키와 인증서 값을 출력하지 마.
6. 설치 중 Codex 또는 Obsidian 재시작이 필요하면 그 지점에서 멈추고, 재시작 후 입력할 정확한 한 문장을 보여줘.
7. 설치가 끝났다고 말하기 전에 doctor 왕복 검증을 실행해 임시 메모리를 만들고 읽고 삭제해줘.
8. 성공 상태가 ready가 아니면 완료라고 말하지 말고 원인과 다음 행동을 알려줘.
9. 설치 명령은 실행 전에 내가 확인해야 하는 외부 설치·커뮤니티 플러그인 동의를 분명히 물어봐.
```

### 설치 중 재시작이 필요한 경우

Codex나 Obsidian을 다시 열었다면 Codex에 다음처럼 입력합니다.

```text
중단된 Codex Obsidian Manuscript Starter 설치를 이어서 진행해줘. 기존 단계를 다시 검증하고 아직 완료되지 않은 단계부터 진행해줘.
```

설치기는 다음 상태를 기록합니다.

```text
preflight → dependency_ready → vault_ready → local_rest_ready → runtime_ready → doctor_verified → ready
```

각 상태에는 API 키나 인증서 값이 저장되지 않습니다. `ready`가 확인되기 전에는 설치가 끝난 것이 아닙니다.

### 방법 B — 직접 명령 실행

PowerShell을 사용할 수 있는 사용자는 다음 명령을 실행할 수 있습니다.

```powershell
codex plugin marketplace add ARTHONG1/codex-obsidian-manuscript-starter --ref v0.3.1
codex plugin add obsidian-manuscript-publisher@codex-obsidian-starter
```

그다음 Codex에 다음을 입력합니다.

```text
옵시디언 원고 환경을 처음부터 설치해줘.
Local REST API 커뮤니티 플러그인을 127.0.0.1 HTTPS 전용으로 설치하는 것에 동의합니다.
```

## 설치가 끝났는지 확인하는 방법

Obsidian이 열린 뒤 Codex에 입력합니다.

```text
옵시디언 연결 상태를 점검해줘.
```

다음 조건을 모두 확인해야 합니다.

- Obsidian이 실행 중입니다.
- 새 보관함이 열려 있습니다.
- Local REST API가 HTTPS loopback으로 연결됩니다.
- 임시 메모리의 생성·읽기·삭제 왕복 검증이 통과합니다.
- doctor 결과가 `ready`입니다.

## 설치 후 바로 하는 일

### 원고 프로젝트 등록

```text
이 프로젝트를 원고 프로젝트로 등록해줘.
```

### 현재 대화 전체 저장

```text
이 대화 전체를 옵시디언 원고 재료로 저장해줘.
```

저장할 때는 현재 대화의 전체 원본과 정리된 원고 재료 카드가 같은 대화 ID 폴더에 분리되어 저장됩니다. 다른 대화의 자료를 임의로 섞지 않습니다.

### 원고 만들기

```text
이 프로젝트의 지정한 대화 재료만 바탕으로 출판 원고형을 만들어줘.
```

```text
이 대화 재료로 플랫폼 독립 범용 블로그형을 만들어줘.
```

```text
이 재료를 출판 원고형과 범용 블로그형으로 각각 만들어줘.
```

### 특정 대화 자료 삭제

```text
이 대화의 옵시디언 자료 묶음만 삭제해줘.
```

현재 대화의 정확한 대화 ID에 해당하는 폴더만 대상으로 합니다. 비슷한 제목의 다른 대화, 다른 원고 버전, 다른 프로젝트는 삭제하지 않습니다.

## 무엇을 만들어 주나요?

### 출판 원고형 (`book_a4`)

- 고정된 원고 양식
- 실제 제작 과정에 맞는 유동적인 Step 1~N
- Skill·플러그인·MCP·AI 에이전트·자동화 도구를 Codex와 함께 만드는 실습 흐름
- Step별 가로형 이미지와 이미지 바로 아래 설명
- A4 HTML·PDF·Markdown

### 플랫폼 독립 범용 블로그형 (`adaptive_blog`)

- 네이버·티스토리·워드프레스에 옮길 수 있는 Markdown·HTML
- 실제 대화와 파일에서 확인된 근거 중심의 글
- 실용 가이드·사례 이야기·인사이트 칼럼 중 주제에 맞는 구조
- 출처·이미지·검증 상태 기록

블로그형 결과물은 `blog.md`와 `blog.html`로 생성됩니다.

AI가 만든 이미지는 실제 화면이라고 속이지 않습니다. 실제 캡처가 아니면 예시 이미지임을 표시하며, 조잡한 placeholder 이미지는 검증에서 거부합니다.
사람이 쓴 글처럼 보인다고 보장하거나 AI 탐지기를 통과한다고 약속하지 않습니다.

## 결과물은 어디에 저장되나요?

검증과 렌더링을 통과한 결과는 `<Windows 바탕화면>\옵시디언 원고` 출판함에 정리됩니다.

```text
옵시디언 원고\
├─ 00 원고 목록.html
├─ 00 사용 방법.txt
├─ 00 Obsidian 보관함 폴더.lnk
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

본문은 `01 본문-복사용.txt`에서 복사합니다. 이미지는 `images` 폴더에서 번호를 확인한 뒤 블로그나 문서 편집기에 직접 올립니다. PDF는 A4 인쇄 확인용이고, 복사·붙여넣기용 기본 파일이 아닙니다.

새 검증본이 나오면 이전 최신본은 `99 이전버전\v0.N`으로 보존됩니다. 네이버·티스토리·워드프레스에 자동 게시하지 않습니다. 최종 붙여넣기와 게시 버튼 확인은 사용자가 수행합니다.

## 문제가 생겼을 때

| 상황 | 해결 방법 |
| --- | --- |
| Python이 없다는 오류 | 공식 Python 설치 안내를 따른 뒤 같은 Codex 설치 요청을 다시 입력합니다. |
| Pillow 또는 ReportLab이 없다는 오류 | 설치 요청을 다시 실행해 고정 버전 패키지를 설치합니다. 임의의 최신 버전을 사용하지 않습니다. |
| WinGet이 없다는 오류 | 공식 Obsidian/Python 다운로드 페이지에서 설치한 뒤 같은 요청을 다시 입력합니다. 비공식 PowerShell 다운로드 명령은 사용하지 않습니다. |
| Codex 또는 Obsidian 재시작 후 중단 | `중단된 Codex Obsidian Manuscript Starter 설치를 이어서 진행해줘.`라고 입력합니다. |
| `Local REST API did not become ready` | Obsidian을 열어 둔 뒤 연결 점검을 다시 요청합니다. HTTP 서버를 켜거나 외부에 포트를 공개하지 않습니다. |
| 보관함이 비어 있지 않다는 오류 | 파일을 지우지 않습니다. 새 빈 폴더를 선택해 다시 설치합니다. |
| Local REST 플러그인이 이미 있다는 오류 | 기존 API 키와 설정을 덮어쓰지 않습니다. 새 빈 보관함을 선택합니다. |
| 설치를 해제하고 싶음 | 연결 정보만 제거하는 uninstall 명령을 사용합니다. 노트·보관함·Obsidian 플러그인은 자동 삭제하지 않습니다. |

## 보안과 데이터 보호

- Local REST API는 `https://127.0.0.1`에서만 사용합니다.
- 커뮤니티 플러그인은 사용자의 명시적 동의가 있어야 설치합니다.
- Local REST API 파일은 URL·SHA-256이 고정된 lock 파일로 검증합니다.
- API 키와 인증서는 저장소·원고·로그에 저장하거나 출력하지 않습니다.
- 기존 보관함과 기존 Local REST 설정은 덮어쓰지 않습니다.
- 대화와 원고는 Local REST 읽기 검증이 통과한 뒤에만 저장 완료로 표시합니다.
- 화면 공유나 캡처에 Local REST 키가 노출됐다면 Obsidian의 `Reset all crypto`로 키를 교체합니다.
- `Re-generate certificates`만 실행해서는 API 키가 바뀌지 않습니다. 인증서와 API 키를 함께 교체해야 하면 `Reset all crypto`를 사용합니다.

## 저작권·브랜드·비제휴 안내

프로젝트 소스 코드는 [`LICENSE`](LICENSE)의 MIT License로 배포합니다. Local REST API, Pillow, ReportLab의 라이선스와 저작권 고지는 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)에 기록합니다.

이 프로젝트는 AI찬우쌤이 만들고 클래스똑딱의 교육 자동화 사례와 함께 소개합니다. 클래스똑딱은 [classddok.com](https://classddok.com/)에서 확인할 수 있습니다.

OpenAI, Codex, Obsidian의 공식 제품·제휴·보증을 의미하지 않으며 각 상표의 권리는 해당 권리자에게 있습니다.

## 개발자 검증

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
python -m pip install -r .\requirements-dev.txt
Invoke-Pester -Script .\tests\InstallerContract.Tests.ps1
Invoke-Pester -Script .\tests\SecretScan.Tests.ps1
python -m unittest discover -s tests -t tests
```

## 라이선스

- 프로젝트: [`LICENSE`](LICENSE)
- 타사 고지: [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)
- 인용 정보: [`CITATION.cff`](CITATION.cff)
- 보안 정책: [`SECURITY.md`](SECURITY.md)

## 변경 이력

### 0.3.1

- Codex만 설치된 Windows 초보자를 위한 설치 흐름을 README와 복붙 프롬프트로 정리했습니다.
- Codex·Obsidian 재시작 후 설치 재개 방법을 전면에 배치했습니다.
- GitHub 첫 화면에서 기능·설치·결과물 위치를 바로 확인할 수 있도록 문서 순서를 바꿨습니다.
- 릴리스 ref와 설치 명령을 v0.3.1로 고정합니다.

### 0.3.0

- Python 의존성 사전 확인과 설치 상태 기록을 추가했습니다.
- `book_a4`와 `adaptive_blog` 출력 프로필을 지원합니다.
- 검증·렌더링·출판·데스크톱 내보내기의 비파괴적 실패 보고를 문서화했습니다.
