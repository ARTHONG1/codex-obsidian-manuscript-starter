# Codex Obsidian Manuscript Starter

Codex 대화를 Obsidian에 대화별로 분리해 보관하고, 검증된 재료를 바탕으로 A4 세로형 한국어 원고를 만드는 Codex 플러그인입니다.

첫 공개판은 **Windows 10/11과 Codex 데스크톱 앱 또는 CLI**를 대상으로 합니다. 사용자는 Codex만 설치되어 있으면 됩니다. Obsidian 설치, 새 보관함 생성, Local REST API 연결, 원고 스킬 설치와 연결 검증은 이 저장소의 설치 스킬이 안내합니다.

## 이 플러그인이 하는 일

- 현재 Codex 대화를 정확한 대화 ID별 폴더로 분리하여 Obsidian에 저장합니다.
- 대화 전체 원본과 원고 재료 카드를 함께 저장합니다.
- 재료를 바탕으로 이미지가 포함된 A4 세로형 HTML·PDF·Markdown 원고를 만듭니다.
- 실습 Step을 완성된 서비스의 사용법이 아니라, Codex에게 Skill·플러그인·MCP·에이전트·자동화 도구를 만들어 달라고 요청하고 검증하는 과정으로 작성합니다.
- Step 수는 실제 제작 과정에 맞게 유동적으로 정하며, 각 Step에는 가로형 AI 생성 이미지와 바로 아래 설명을 넣습니다.
- 특정 대화의 Obsidian 묶음만 명시적으로 삭제할 수 있습니다. 다른 대화와 원고 버전은 삭제하지 않습니다.

## 3분 설치

아래의 `<OWNER>/<REPOSITORY>`를 이 저장소의 실제 GitHub 주소로 바꿉니다.

```powershell
codex plugin marketplace add <OWNER>/<REPOSITORY>
codex plugin add obsidian-manuscript-publisher@codex-obsidian-starter
```

그다음 Codex에서 다음과 같이 말합니다.

```text
옵시디언 원고 환경을 처음부터 설치해줘.
Local REST API 커뮤니티 플러그인을 127.0.0.1 HTTPS 전용으로 설치하는 것에 동의합니다.
```

Codex가 Obsidian 설치 여부와 보관함 위치를 확인하고, 필요한 경우 Obsidian을 설치합니다. 새 보관함은 기본적으로 `문서\Codex Obsidian Manuscript`에 만듭니다. 기존 파일이 있는 폴더는 절대 덮어쓰지 않습니다.

Obsidian이 열린 뒤에는 Codex에 다음과 같이 말합니다.

```text
옵시디언 연결 상태를 점검해줘.
```

설정이 끝났다는 말만 믿지 않습니다. 진단 과정은 Obsidian 안에 임시 메모를 만들고, 다시 읽고, 삭제하는 실제 왕복 검증을 통과해야 `ready`로 끝납니다.

## 바로 쓰는 요청문

```text
이 프로젝트를 원고 프로젝트로 등록해줘.
```

```text
이 대화 전체를 옵시디언 원고 재료로 저장해줘.
```

```text
이 프로젝트의 지정한 대화 재료만 바탕으로 Part 1-01 원고를 만들어줘.
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
- 기존 보관함, 기존 Local REST API 폴더, 기존 설정은 덮어쓰지 않습니다. 별도의 빈 폴더를 선택하거나 기존 환경을 유지해야 합니다.
- 대화·원고 저장은 Local REST API의 읽기 검증이 통과한 뒤에만 완료로 표시합니다. 연결이 끊기면 보관함에 직접 복사하는 우회 경로를 사용하지 않습니다.

## 문제가 생겼을 때

| 상황 | 안전한 해결 방법 |
| --- | --- |
| `Local REST API did not become ready` | Obsidian을 열어 둔 뒤 Codex에 연결 점검을 다시 요청합니다. HTTP 서버를 켜거나 포트를 외부 공개하지 않습니다. |
| 보관함이 비어 있지 않다는 오류 | 해당 폴더의 파일을 지우지 않습니다. 새 빈 폴더를 선택하거나 기존 보관함을 그대로 사용합니다. |
| Local REST 플러그인이 이미 있다는 오류 | 기존 API 키와 설정을 덮어쓰지 않습니다. 기존 환경을 점검하거나 새 보관함을 선택합니다. |
| 설치를 해제하고 싶음 | `bootstrap\\uninstall.ps1 -RemoveRuntimeConfig`는 연결 정보만 지우며, 노트·보관함·Obsidian 플러그인은 삭제하지 않습니다. |

## 개발·검증

저장소를 내려받아 수정하는 개발자는 PowerShell에서 다음 검증을 실행합니다.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
python -m pip install -r .\requirements-dev.txt
Invoke-Pester -Script .\tests\InstallerContract.Tests.ps1
Invoke-Pester -Script .\tests\SecretScan.Tests.ps1
```

배포 전에는 플러그인 구조 검사, 비밀값 검사, PowerShell 계약 테스트, Python 원고 스크립트 테스트를 모두 통과해야 합니다. 실제 사용자의 보관함이나 API 키를 테스트 저장소에 넣지 마십시오.

## 배포자 체크리스트

1. `.codex-plugin/plugin.json`의 버전과 릴리스 노트를 갱신합니다.
2. Local REST API를 갱신할 경우 새 릴리스 파일을 직접 검증하고 `dependencies.lock.json`의 URL·SHA-256을 함께 갱신합니다.
3. 빈 Windows 테스트 계정에서 설치 → Obsidian 실행 → doctor `ready` → 대화 저장 → 원고 생성 → 대화 묶음 삭제까지 확인합니다.
4. API 키, `data.json`, 인증서, 개인 보관함, 원고 원문, 개인 경로가 Git 상태에 없는지 확인합니다.
5. GitHub 저장소를 공개한 뒤 이 README의 `<OWNER>/<REPOSITORY>`를 실제 주소로 교체합니다.

## 라이선스

[MIT License](LICENSE)
