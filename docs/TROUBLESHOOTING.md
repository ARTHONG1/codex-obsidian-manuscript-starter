# 문제 해결

| 상황 | 해결 방법 |
| --- | --- |
| Python이 없음 | 공식 Python을 설치한 뒤 같은 Codex 설치 요청을 다시 입력합니다. |
| Pillow·ReportLab이 없음 | 설치 요청을 다시 실행해 `requirements.txt`의 고정 버전을 설치합니다. |
| WinGet이 없음 | 공식 Obsidian 또는 Python 설치 페이지에서 설치한 뒤 재시작 문장을 입력합니다. |
| Codex·Obsidian 재시작 | `중단된 Codex Obsidian Manuscript Starter 설치를 이어서 진행해줘.`라고 입력합니다. |
| REST 연결 실패 | Obsidian을 열고 `옵시디언 연결 상태를 점검해줘.`라고 입력합니다. HTTP 서버를 외부에 공개하지 않습니다. |
| 기존 보관함 오류 | 기존 폴더를 비우지 말고 새 빈 보관함을 선택합니다. |
| API 키 노출 | Obsidian Local REST 설정에서 `Reset all crypto`를 실행합니다. 키를 대화나 문서에 복사하지 않습니다. |

| runtime 재시작 후 이어가기 | schema-v2 runtime을 다시 읽고 제품 소유 venv와 남은 설치 단계를 재검증합니다. |
| Local REST 설정이 비어 있거나 부분적으로 저장됨 | Obsidian을 열어 둔 상태에서 준비 점검을 다시 요청합니다. 준비 확인은 일시적인 파일·JSON 상태를 재시도합니다. |
| 제품 Python 환경 확인 | 전역 패키지를 수정하지 말고 제품 소유 venv에서 `requirements.lock.txt`의 해시 잠금 세트를 사용합니다. |

검증 명령은 다음과 같습니다.

```powershell
.\ci\run-all-tests.ps1 -PythonPath $Python312 -ExpectedPythonSkipCount 4
```

현재 허용하는 Python 건너뜀은 정확히 네 건입니다. 실 wheelhouse가 제공되지 않은 `test_real_wheelhouse_recreates_committed_lock_when_provided`, 현재 권한에서 디렉터리 reparse point를 만들 수 없는 `test_existing_item_reparse_point_is_rejected_when_supported`, `test_rejects_reparse_point_without_following_it_when_supported`, `test_snapshot_rejects_reparse_staging_parent_when_supported`입니다. 다른 수가 보고되면 원인을 조사하고 검증을 통과시키기 위해 기대값을 올리지 않습니다.
