# 설치 안내

## 기본 흐름

Codex만 설치한 사용자는 README의 설치 문장을 Codex에 붙여넣습니다. Codex가 플러그인을 설치하기 전 커뮤니티 플러그인과 외부 프로그램 설치 동의를 확인해야 합니다.

설치 대상은 다음과 같습니다.

1. Obsidian
2. 새 빈 Obsidian 보관함
3. Obsidian Local REST API
4. Python과 Pillow·ReportLab
5. Codex 원고 스킬 연결

Python 런타임은 제품 소유 venv에 설치하며 사용자 전역 Python 패키지를 사용하지 않습니다. 직접 런타임 패키지는 `Pillow==12.3.0`, `reportlab==4.4.3`, `python-docx==1.2.0`, `pdfplumber==0.11.9`, `pypdfium2==5.12.1`, `pypdf==5.9.0`이고, 전이 의존성은 `requirements.lock.txt`의 해시 잠금 세트에서 설치합니다.

기존 보관함은 자동으로 채택하지 않습니다. 기존 파일이 있는 폴더를 지정하면 설치를 멈추고 새 빈 폴더를 요청합니다.

## 재시작

Codex 또는 Obsidian이 재시작되면 아래 문장을 입력합니다.

```text
중단된 Codex Obsidian Manuscript Starter 설치를 이어서 진행해줘.
```

설치가 끝났다는 메시지보다 `옵시디언 연결 상태를 점검해줘`의 `ready` 결과를 기준으로 판단합니다.

재시작 후 schema-v2 runtime을 다시 읽습니다. Local REST 설정 파일이 없거나 비어 있거나 아직 완성되지 않은 동안에는 준비 확인을 재시도하며, WinGet이 없으면 공식 설치 페이지에서 Obsidian과 Python을 설치한 뒤 이어가기 문장을 입력합니다.

개발 검증은 저장소 루트에서 다음 집계 명령으로 실행합니다.

```powershell
.\ci\run-all-tests.ps1 -PythonPath $Python312 -ExpectedPythonSkipCount 4
```

현재 허용하는 Python 건너뜀은 정확히 네 건입니다. 실 wheelhouse가 제공되지 않은 `test_real_wheelhouse_recreates_committed_lock_when_provided`, 현재 권한에서 디렉터리 reparse point를 만들 수 없는 `test_existing_item_reparse_point_is_rejected_when_supported`, `test_rejects_reparse_point_without_following_it_when_supported`, `test_snapshot_rejects_reparse_staging_parent_when_supported`이며, 다른 수가 보고되면 검증은 실패해야 합니다.
