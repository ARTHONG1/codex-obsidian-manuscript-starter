# Codex Obsidian Manuscript Starter

Codex 대화를 Obsidian에 대화별로 분리해 보관하고, 검증된 재료를 바탕으로 A4 세로형 한국어 원고 또는 플랫폼 독립 블로그를 만드는 Codex 플러그인입니다.

첫 공개판은 **Windows 10/11과 Codex 데스크톱 앱 또는 CLI**를 대상으로 합니다. 사용자는 Codex만 설치되어 있으면 됩니다. Obsidian 설치, 새 보관함 생성, Local REST API 연결, 원고 스킬 설치와 연결 검증은 이 저장소의 설치 스킬이 안내합니다.

## 이 플러그인이 하는 일

- 현재 Codex 대화를 정확한 대화 ID별 폴더로 분리하여 Obsidian에 저장합니다.
- 대화 전체 원본과 원고 재료 카드를 함께 저장합니다.
- 재료를 바탕으로 이미지가 포함된 A4 세로형 HTML·PDF·Markdown 원고를 만듭니다.
- 같은 재료를 네이버·티스토리·워드프레스 등에 옮길 수 있는 Markdown·HTML 블로그로도 만듭니다.
- PDF·DOCX·PNG·JPG·WEBP 원고 예시를 분석해 사용자 양식 후보를 만들고, 미리보기와 명시적 승인 후 불변 `t0.N` 템플릿으로 등록합니다.
- 승인한 사용자 양식으로 custom Markdown·HTML·PDF 원고를 만들고 바탕화면 출판함으로 내보냅니다.
- 실습 Step을 완성된 서비스의 사용법이 아니라, Codex에게 Skill·플러그인·MCP·에이전트·자동화 도구를 만들어 달라고 요청하고 검증하는 과정으로 작성합니다.
- Step 수는 실제 제작 과정에 맞게 유동적으로 정하며, 각 Step에는 가로형 AI 생성 이미지와 바로 아래 설명을 넣습니다.
- 특정 대화의 Obsidian 묶음만 명시적으로 삭제할 수 있습니다. 다른 대화와 원고 버전은 삭제하지 않습니다.

## 3분 설치

Codex 채팅창에 아래 내용을 그대로 붙여넣습니다.

```text
GitHub의 ARTHONG1/codex-obsidian-manuscript-starter v0.5.1를 처음부터 설치해줘.
나는 Codex만 설치한 초보자야. Obsidian 설치, 새 빈 보관함 생성, Local REST API 연결, 원고 스킬 설치와 연결 확인까지 진행해줘.
기존 Obsidian 보관함과 기존 설정은 건드리지 말고, API 키와 인증서 값은 출력하지 마.
설치나 커뮤니티 플러그인 동의가 필요하면 먼저 나에게 물어봐.
Codex 또는 Obsidian 재시작이 필요하면 재시작 후 입력할 문장도 알려줘.
doctor 왕복 검증이 ready가 될 때까지 설치 완료라고 말하지 마.
```

Codex가 설치 명령을 직접 실행할 수 없는 환경이라면 PowerShell에서 다음 두 명령을 실행한 뒤 위의 설치 요청을 입력합니다.

이미 쓰고 있는 Obsidian 보관함을 그대로 연결하는 기능은 아직 없습니다. 설치 대상은 전용 새 빈 폴더이며, 새 빈 보관함을 사용합니다.

```powershell
codex plugin marketplace add ARTHONG1/codex-obsidian-manuscript-starter --ref v0.5.1
codex plugin add obsidian-manuscript-publisher@codex-obsidian-starter
```

사용자 양식 등록은 다음 순서로 진행합니다. PDF·DOCX·이미지를 분석해도 첫 요청에서 등록하지 않고, 안전성 검사·구조 분석·HTML/PDF 미리보기·미확정 항목을 먼저 보여 줍니다. 사용자가 정확한 candidate ID를 승인한 뒤에만 `t0.N`으로 등록합니다. 등록과 원고 발행은 Local REST 되읽기 검증이 통과한 경우에만 완료로 표시합니다.

```text
이 PDF를 분석해서 ‘출판사 A 원고형’ 템플릿 후보를 만들어줘.
미리보기와 검증 결과를 확인했어. candidate ID가 정확히 일치하는지 확인한 뒤 이 후보를 승인하고 등록해줘.
이 대화 재료로 ‘출판사 A 원고형’ custom 원고를 만들어 검증 완료 출판함으로 내보내줘.
```

설치 중 Codex나 Obsidian을 다시 시작했다면 다음 문장으로 이어갑니다.

```text
중단된 Codex Obsidian Manuscript Starter 설치를 이어서 진행해줘.
```

설치가 끝나면 Codex에 다음을 입력합니다.

```text
옵시디언 연결 상태를 점검해줘.
```

연결 점검은 Obsidian 안에 임시 메모리를 만들고, 다시 읽고, 삭제하는 왕복 검증을 통과해야 `ready`로 끝납니다.

원고를 출판할 때는 Codex에 `검증 완료 원고 출판함으로 만들어줘`라고 요청합니다. 선택한 `v0.N`을 새로 검증하고 렌더링한 뒤 Vault 발행과 바탕화면 export 결과를 따로 보고합니다. `desktop_export_status: export_failed`가 나오면 같은 버전을 덮어쓰지 않고 원인을 수정한 뒤 새 `v0.N`으로 다시 요청합니다.

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
이 대화 재료로 플랫폼 독립 범용 블로그형을 만들어줘.
```

```text
이 PDF를 분석해서 ‘출판사 A 원고형’ 템플릿 후보를 만들어줘.
```

```text
현재 활성 후보를 승인하고 ‘출판사 A 원고형’ 템플릿으로 등록해줘.
```

```text
이 대화 재료로 ‘출판사 A 원고형’ 원고를 만들어줘.
```

```text
이 대화의 옵시디언 자료 묶음만 삭제해줘.
```

마지막 요청은 현재 대화의 정확한 대화 ID에 해당하는 폴더만 대상으로 합니다. 비슷한 제목의 다른 대화, 다른 원고 버전, 다른 프로젝트는 건드리지 않습니다.

## 두 가지 출력 형식

- 출판 원고형 (`book_a4`): 기존 고정 원고 양식, 유동적인 Step 1~N, 가로형 이미지, A4 HTML·PDF·Markdown을 만듭니다.
- 범용 블로그형 (`adaptive_blog`): 실제 대화와 파일에서 확인된 근거를 바탕으로 `blog.md`와 `blog.html`을 만듭니다.

AI가 만든 이미지는 실제 화면이라고 속이지 않습니다. 실제 캡처가 아니면 예시 이미지임을 표시하며, 조잡한 이미지는 검증에서 거부합니다. 사람이 쓴 글처럼 보인다고 보장하거나 AI 탐지기를 통과한다고 약속하지 않습니다.

## 검증 완료 원고 출판함

검증과 렌더링을 통과한 결과는 `<Windows 바탕화면>\옵시디언 원고`에 정리됩니다.

```text
옵시디언 원고\
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

`01 본문-복사용.txt`에서 글을 복사하고, `images` 폴더의 번호에 맞춰 이미지를 올립니다. `03 미리보기.html`에서 결과를 확인합니다. 책의 PDF는 A4 화면·인쇄 확인용입니다.

새 검증본이 나오면 이전 최신본은 `99 이전버전\v0.N`으로 보존됩니다. 네이버·티스토리·워드프레스에 자동 게시하지 않습니다.

자세한 설치는 [설치 안내](docs/INSTALL_GUIDE.md), 결과물 사용법은 [사용 안내](docs/USAGE_GUIDE.md), 오류 해결은 [문제 해결](docs/TROUBLESHOOTING.md)을 참고합니다.

개발자가 설치된 스킬을 저장소와 맞출 때는 테스트가 모두 통과한 뒤 `verify_skill_sync.py`의 해시 비교·백업 승격 절차를 사용합니다. 이 유지보수 절차는 일반 사용자의 자동 설치에 포함되지 않습니다.

## 보안과 데이터 보호

- Obsidian Local REST API는 `https://127.0.0.1`에서만 사용합니다.
- 커뮤니티 플러그인은 사용자의 명시적 동의가 있어야 설치합니다.
- 설치되는 Local REST API 버전과 파일 해시는 `dependencies.lock.json`에 고정되어 있습니다.
- API 키와 인증서는 저장소, 원고, 로그에 저장하거나 출력하지 않습니다.
- 기존 보관함, 기존 Local REST API 폴더, 기존 설정은 덮어쓰지 않습니다.
- 기존 파일이 있는 폴더는 절대 덮어쓰지 않습니다.
- 대화·원고 저장은 Local REST API의 읽기 검증이 통과한 뒤에만 완료로 표시합니다.
- 화면에 API 키가 노출됐다면 `Reset all crypto`로 키를 교체합니다. `Re-generate certificates`만으로는 API 키가 바뀌지 않습니다.

## 설치 기준

설치기는 사용자 보관함과 분리된 제품 소유 Python 3.12 가상환경을 사용합니다. 재시작 뒤에는 schema-v2 runtime을 다시 읽고, Local REST가 준비될 때까지 재시도합니다. WinGet이 없으면 Obsidian과 Python은 공식 설치 페이지에서 먼저 설치해야 합니다.

직접 런타임 패키지는 `Pillow==12.3.0`, `reportlab==4.4.3`, `python-docx==1.2.0`, `pdfplumber==0.11.9`, `pypdfium2==5.12.1`, `pypdf==5.9.0` 여섯 개이며, 나머지 전이 의존성은 `requirements.lock.txt`의 SHA-256 해시로 고정합니다. 설치 경로와 재시작 문장은 [설치 안내](docs/INSTALL_GUIDE.md), beginner prompt는 [INSTALL_PROMPT.md](INSTALL_PROMPT.md)에 있습니다.

## 저작권·브랜드·비제휴 안내

프로젝트 소스 코드는 [`LICENSE`](LICENSE)의 MIT License로 배포합니다. 타사 라이선스는 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)에 기록합니다.

이 프로젝트는 AI찬우쌤이 만들고 [클래스똑딱](https://classddok.com/)의 교육 자동화 사례와 함께 소개합니다. OpenAI, Codex, Obsidian의 공식 제품·제휴·보증을 의미하지 않습니다.

## 문제가 생겼을 때

| 상황 | 안전한 해결 방법 |
| --- | --- |
| Python, Pillow, ReportLab이 없다는 오류 | 같은 Codex 설치 요청을 다시 입력합니다. 공식 설치 경로와 고정 버전을 사용합니다. |
| WinGet이 없다는 오류 | 공식 Obsidian/Python 설치 페이지에서 설치한 뒤 같은 요청을 다시 입력합니다. |
| `Local REST API did not become ready` | Obsidian을 열어 둔 뒤 연결 점검을 다시 요청합니다. HTTP 서버를 외부에 공개하지 않습니다. |
| 보관함이 비어 있지 않다는 오류 | 파일을 지우지 않습니다. 새 빈 폴더를 선택합니다. |
| Local REST 플러그인이 이미 있다는 오류 | 기존 API 키와 설정을 덮어쓰지 않습니다. 새 보관함을 선택합니다. |
| 설치를 해제하고 싶음 | 연결 정보만 제거하는 uninstall 명령을 사용합니다. 노트·보관함·플러그인은 자동 삭제하지 않습니다. |

## 라이선스

[MIT License](LICENSE) · [타사 고지](THIRD_PARTY_NOTICES.md) · [보안 정책](SECURITY.md)

## 개발·검증

저장소를 수정하는 개발자는 PowerShell에서 다음 검증 명령을 실행합니다.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\ci\run-python-tests.ps1 -PythonPath $Python312
.\ci\run-pester-tests.ps1 -Path .\tests\InstallerContract.Tests.ps1,.\tests\PythonRuntimeContract.Tests.ps1,.\tests\SecretScan.Tests.ps1 -ExpectedSkipCount 0
.\ci\run-all-tests.ps1 -PythonPath $Python312
```

## Master Editorial Quality V3

New book packages use the V3 editorial profile. Step count follows the real build process for a Skill, plugin, MCP, AI agent, automation, web app, or document generator; it is not a fixed usage tutorial. Step prose is 2-4 sentences, tips are evidence-driven, and the package is blocked below the 85-point quality gate.

V3 visuals are Codex built-in `generated_scene` assets: topic-specific, wide, print-legible software screens, work products, workflows, results, or field scenes. The generator must not add red boxes, numbered callouts, arrows, borders, or generic AI decoration.

Example request:

```text
Create a Master Editorial Quality V3 book from the selected conversation materials. Show the real process of building the technology with Codex or the named tool, choose only the Steps the topic needs, and generate professional wide visuals tied to each artifact. Do not add red boxes, numbered callouts, or arrows.
```
