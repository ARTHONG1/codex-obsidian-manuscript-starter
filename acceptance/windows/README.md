# Beginner Windows acceptance

이 디렉터리는 Codex만 설치된 초보자 흐름을 검증하기 위한 격리 테스트 계약입니다.

실제 `Codex-only`, `no-WinGet`, 재시작, Obsidian, Local REST 검증은 Windows Sandbox·일회성 VM·새 Windows 계정에서만 실행합니다. 개발자 계정의 Vault, Codex 설정, 바탕화면 출판함을 테스트 대상으로 사용하지 않습니다.

```powershell
.\ci\run-beginner-install-acceptance.ps1 -ScenarioSet .\acceptance\windows\scenarios.json -Root (Join-Path $env:TEMP ("codex-acceptance-" + [guid]::NewGuid().ToString("N"))) -EvidencePath .\artifacts\beginner-acceptance.json
```

실패한 경우에도 증거 JSON을 남겨야 합니다. 증거에는 시나리오 ID, 상태 코드, 상호작용 수, 격리 루트의 상대 자산 이름만 기록하며 사용자 이름, 개인 경로, API 키, 인증서, 대화, 원고 내용은 기록하지 않습니다.
