# Codex Obsidian Manuscript Starter

Codex 대화를 Obsidian에 대화별로 분리해 보관하고, 검증된 재료를 바탕으로 A4 세로형 한국어 원고 또는 플랫폼 독립 블로그를 만드는 Codex 플러그인입니다.

첫 공개판은 **Windows 10/11과 Codex 데스크톱 앱 또는 CLI**를 대상으로 합니다. Obsidian 설치, 새 보관함 생성, Local REST API 연결, 원고 스킬 설치와 연결 검증은 이 저장소의 설치 스킬이 안내합니다.

> **설치 전 확인 사항**
> - 이 버전은 **전용 새 빈 폴더**에 새 보관함을 만들어야 합니다. 이미 쓰고 있는 Obsidian 보관함을 그대로 연결하는 기능은 아직 없습니다.
> - 설치 스크립트가 Python과 고정 버전의 `Pillow`, `reportlab`을 먼저 확인합니다. Python이 없으면 WinGet으로 공식 Python 패키지를 설치하고, WinGet도 없으면 공식 다운로드 주소를 안내한 뒤 같은 명령으로 재개합니다.

## 이 플러그인이 하는 일

- 현재 Codex 대화를 정확한 대화 ID별 폴더로 분리하여 Obsidian에 저장합니다.
- 대화 전체 원본과 원고 재료 카드를 함께 저장합니다.
- 재료를 바탕으로 이미지가 포함된 A4 세로형 HTML·PDF·Markdown 원고를 만듭니다.
- 같은 재료를 네이버·티스토리·워드프레스 등에 옮길 수 있는 Markdown·HTML 블로그로도 만듭니다.
- 실습 Step을 완성된 서비스의 사용법이 아니라, Codex에게 Skill·플러그인·MCP·에이전트·자동화 도구를 만들어 달라고 요청하고 검증하는 과정으로 작성합니다.
- Step 수는 실제 제작 과정에 맞게 유동적으로 정하며, 각 Step에는 가로형 AI 생성 이미지와 바로 아래 설명을 넣습니다.
- 특정 대화의 Obsidian 묶음만 명시적으로 삭제할 수 있습니다. 다른 대화와 원고 버전은 삭제하지 않습니다.

## 두 가지 출력 형식

- 출판 원고형 (`book_a4`): 기존 고정 원고 양식, 유동적인 Step 1~N, 가로형 생성 이미지, A4 HTML·PDF·Markdown을 만듭니다. 출력 형식을 말하지 않으면 이 형식이 기본입니다.
- 범용 블로그형 (`adaptive_blog`): 책 원고를 단순히 줄이는 대신 자료의 성격을 판단해 실용 가이드, 사례 이야기, 인사이트 칼럼 중 하나로 새롭게 구성합니다. `blog.md`와 `blog.html`을 함께 만들어 특정 블로그 플랫폼에 종속되지 않습니다.

블로그형은 실제 대화와 파일에서 확인된 근거, 선택 이유, 오류와 수정, 검증 결과를 글의 중심에 둡니다. 상투적인 도입·마무리, 과장 제목, 근거 없는 1인칭 경험, 조잡한 AI 이미지는 검증 단계에서 거부합니다. 다만 사람처럼 보인다고 보장하거나 AI 탐지기를 통과한다고 약속하지는 않습니다.

## 검증 완료 원고 출판함

검증과 렌더링을 통과한 결과는 기본적으로 `<Windows 바탕화면>\옵시디언 원고`에 한 번 더 정리됩니다. Obsidian 보관함은 대화와 원고의 원본 기록을 보존하고, 바탕화면 출판함은 글을 복사하고 이미지를 올리기 쉽게 만든 읽기·전달용 결과입니다. 출판함에서 파일을 고쳐도 Obsidian 원본으로 역동기화되지 않습니다.

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

처음 사용하는 분은 다음 순서만 따르면 됩니다.

1. `00 원고 목록.html`에서 원하는 원고의 `00 최신본`을 엽니다.
2. `01 본문-복사용.txt`의 글을 복사해 블로그나 문서 편집기에 붙여넣습니다. 본문에는 `[이미지 02 삽입: ...]`처럼 이미지 자리가 표시됩니다.
3. 책은 `05 이미지-삽입순서.md`, 블로그는 `04 이미지-삽입순서.md`를 열고 `images` 폴더의 같은 번호 파일을 표시된 자리에 올립니다.
4. `03 미리보기.html`에서 글과 이미지 순서를 확인합니다. 책의 `04 인쇄용.pdf`는 A4 화면·인쇄 확인용이며, 글을 복사하는 기본 파일은 아닙니다.

새 검증본이 나오면 이전 `00 최신본`은 `99 이전버전\v0.N`으로 보존됩니다. 과거 버전은 자동으로 모두 복사하지 않으며, 프로젝트·출력 형식·버전을 정확히 지정했을 때만 추가합니다. 네이버·티스토리·워드프레스에 자동 게시하지 않습니다. 최종 붙여넣기, 이미지 업로드, 플랫폼 미리보기와 게시 버튼 확인은 사용자가 수행합니다.

다시 내보내거나 특정 과거 검증본을 정리하려면 Codex에 다음처럼 요청합니다.

```text
바탕화면 출판함만 다시 만들어줘.
```

```text
AAA AI Agent Automation 프로젝트의 범용 블로그형 v0.3 검증본을 출판함에 정리해줘.
```

Obsidian 게시와 바탕화면 내보내기는 서로 다른 결과입니다. Obsidian이 닫혀 Local REST 게시가 실패해도 로컬 검증본이 온전하면 출판함 내보내기는 성공할 수 있으며, Codex는 두 상태를 따로 알려 줍니다. 실패한 내보내기는 기존 `00 최신본`을 바꾸지 않습니다.

## 처음 설치하는 Windows 사용자

```powershell
codex plugin marketplace add ARTHONG1/codex-obsidian-manuscript-starter --ref v0.3.0
codex plugin add obsidian-manuscript-publisher@codex-obsidian-starter
```

그다음 Codex에서 다음과 같이 말합니다.

```text
옵시디언 원고 환경을 처음부터 설치해줘.
Local REST API 커뮤니티 플러그인을 127.0.0.1 HTTPS 전용으로 설치하는 것에 동의합니다.
```

Codex가 Obsidian 설치 여부와 보관함 위치를 확인하고, 필요한 경우 Obsidian을 설치합니다. 새 보관함은 기본적으로 `문서\Codex Obsidian Manuscript`에 만듭니다. 기존 파일이 있는 폴더는 절대 덮어쓰지 않습니다.

설치 중 Codex 또는 Obsidian이 재시작되면 같은 요청을 다시 입력합니다. 설치기는 `preflight → dependency_ready → vault_ready → local_rest_ready → runtime_ready → doctor_verified → ready` 상태를 기록하고, 재실행할 때 완료 상태를 재검증한 뒤 안전한 작업만 다시 수행합니다. 설치 상태에는 API 키나 인증서 값이 저장되지 않습니다.

WinGet이 없는 Windows에서는 설치를 중단하고 공식 Python 또는 Obsidian 다운로드 주소를 안내합니다. 안내된 공식 설치를 완료한 뒤 같은 명령을 다시 실행하면 됩니다. 비공식 PowerShell 다운로드 명령은 사용하지 않습니다.

Obsidian이 열린 뒤에는 Codex에 다음과 같이 말합니다.

```text
옵시디언 연결 상태를 점검해줘.
```

설정이 끝났다는 말만 믿지 않습니다. 진단 과정은 Obsidian 안에 임시 메모를 만들고, 다시 읽고, 삭제하는 실제 왕복 검증을 통과해야 `ready`로 끝납니다.

## 바로 쓰는 요청문

```text
이 프로젝트를 원고 프로젝트로 등록해줘.
```

## 저작권·브랜드·비제휴 안내

이 프로젝트의 소스 코드는 `LICENSE`의 MIT License로 배포합니다. Python Pillow, ReportLab, Obsidian Local REST API의 라이선스와 저작권 고지는 `THIRD_PARTY_NOTICES.md`에 따로 기록합니다.

이 프로젝트는 AI찬우쌤이 만들고 클래스똑딱의 교육 자동화 사례와 함께 소개합니다. 클래스똑딱은 [classddok.com](https://classddok.com/)에서 확인할 수 있습니다. OpenAI, Codex, Obsidian의 공식 제품·제휴·보증을 의미하지 않으며 각 상표의 권리는 해당 권리자에게 있습니다.

```text
이 대화 전체를 옵시디언 원고 재료로 저장해줘.
```

```text
이 프로젝트의 지정한 대화 재료만 바탕으로 Part 1-01 원고를 만들어줘.
```

```text
이 대화 재료로 플랫폼 독립 범용 블로그형을 만들어줘.
```

```text
이 재료를 출판 원고형과 범용 블로그형으로 각각 만들어줘.
```

```text
이 대화의 옵시디언 자료 묶음만 삭제해줘.
```

마지막 요청은 현재 대화의 정확한 대화 ID에 해당하는 폴더만 대상으로 합니다. 비슷한 제목의 다른 대화, 다른 원고 버전, 다른 프로젝트는 건드리지 않습니다.

## 보안과 데이터 보호

- Obsidian Local REST API는 `https://127.0.0.1`에서만 사용합니다. 비암호화 HTTP 서버나 외부 네트워크 공개를 사용하지 않습니다.
- 커뮤니티 플러그인은 사용자의 명시적 동의가 있어야만 설치합니다.
- 설치되는 Local REST API 버전과 파일 해시는 [`dependencies.lock.json`](dependencies.lock.json)에 고정되어 있습니다. 내려받은 파일의 SHA-256이 다르면 설치를 중단합니다.
- API 키는 Obsidian 보관함의 플러그인 설정에만 생성됩니다. 이 저장소, 런타임 설정 파일, 원고, 로그에 저장하거나 출력하지 않습니다.
- Local REST 키가 화면 공유나 캡처에 노출되었다면 Obsidian 플러그인 설정에서 `Reset all crypto`를 직접 실행해 키를 교체합니다. `Re-generate certificates`만 실행하면 API 키는 바뀌지 않습니다. 새 키를 문서나 대화에 복사하지 않습니다.
- 기존 보관함, 기존 Local REST API 폴더, 기존 설정은 덮어쓰지 않습니다. 설치는 **전용 새 빈 폴더**를 지정해야 진행됩니다. 이미 쓰고 있는 보관함을 그대로 연결하는 경로는 이 버전에 없습니다.
- 대화·원고 저장은 Local REST API의 읽기 검증이 통과한 뒤에만 완료로 표시합니다. 연결이 끊기면 보관함에 직접 복사하는 우회 경로를 사용하지 않습니다.

## 문제가 생겼을 때

| 상황 | 안전한 해결 방법 |
| --- | --- |
| `Local REST API did not become ready` | Obsidian을 열어 둔 뒤 Codex에 연결 점검을 다시 요청합니다. HTTP 서버를 켜거나 포트를 외부 공개하지 않습니다. |
| 보관함이 비어 있지 않다는 오류 | 해당 폴더의 파일을 지우지 않습니다. 아직 존재하지 않는 **새 빈 폴더 경로**를 `-VaultPath`에 지정해 다시 실행합니다. 오류 메시지에 막고 있는 폴더 경로가 표시됩니다. |
| Local REST 플러그인이 이미 있다는 오류 | 기존 API 키와 설정을 덮어쓰지 않습니다. 아직 존재하지 않는 **새 빈 폴더 경로**를 `-VaultPath`에 지정해 다시 실행합니다. |
| 설치를 해제하고 싶음 | `bootstrap\\uninstall.ps1 -RemoveRuntimeConfig`는 연결 정보만 지우며, 노트·보관함·Obsidian 플러그인은 삭제하지 않습니다. |

## 개발·검증

저장소를 내려받아 수정하는 개발자는 PowerShell에서 다음 검증을 실행합니다.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
python -m pip install -r .\requirements-dev.txt
Invoke-Pester -Script .\tests\InstallerContract.Tests.ps1
Invoke-Pester -Script .\tests\SecretScan.Tests.ps1
python -m unittest discover -s tests -t tests
```

배포 전에는 플러그인 구조 검사, 비밀값 검사, PowerShell 계약 테스트, Python 원고 스크립트 테스트를 모두 통과해야 합니다. 실제 사용자의 보관함이나 API 키를 테스트 저장소에 넣지 마십시오.

## 배포자 체크리스트

1. `.codex-plugin/plugin.json`의 버전과 릴리스 노트를 갱신합니다.
2. Local REST API를 갱신할 경우 새 릴리스 파일을 직접 검증하고 `dependencies.lock.json`의 URL·SHA-256을 함께 갱신합니다.
3. 빈 Windows 테스트 계정에서 설치 → Obsidian 실행 → doctor `ready` → 대화 저장 → 원고 생성 → 대화 묶음 삭제까지 확인합니다.
4. API 키, `data.json`, 인증서, 개인 보관함, 원고 원문, 개인 경로가 Git 상태에 없는지 확인합니다.
5. GitHub 저장소가 공개 상태이고 위의 설치 주소가 실제 저장소 주소와 일치하는지 확인합니다.

## 라이선스

[MIT License](LICENSE)

## 변경 이력

### 0.2.0

- `book_a4`와 `adaptive_blog` 출력 프로필을 지원합니다.
- 검증·렌더링·출판·데스크톱 내보내기의 결정적 오류 코드와 비파괴적 실패 보고를 문서화했습니다.
- 문서와 테스트는 실제 실행한 검증 수치만 완료 근거로 사용합니다.
> - 출판함 최상위에서 Windows가 자동으로 만든 `desktop.ini`, `Thumbs.db`, macOS의 `.DS_Store`만 허용합니다. 그 밖의 파일은 실수로 덮어쓰지 않도록 파일명을 포함해 중단합니다.
