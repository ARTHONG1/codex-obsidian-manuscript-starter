# Conversation Workflow

Use this reference for registration, archive, refresh, exclusion, and pause requests.

Confirm the active Codex task belongs to the exact registered project. Read only that task/thread, follow cursors until no older turn remains, normalize readable turns with stable IDs, and never scan other conversations.

For `이 프로젝트를 원고 프로젝트로 등록해줘`, update only the matching registry entry and create the project brief, `00 Conversations`, `01 Manuscript`, and `02 Blog` through HTTPS Local REST when absent.

For `이 대화 전체를 옵시디언에 저장해줘`, `이 대화 원고 재료 최신화해줘`, or `이 대화 옵시디언에 정리해줘`, run `scripts/archive_conversation.py` against a staging `00 Conversations` root. The bundle contains `conversation.md`, `material-card.md`, `metadata.json`, and `assets/`; publish each changed file through `publish_bundle` and require byte-for-byte readback before reporting `archived` or `materials_refreshed`.

The archive command accepts a UTF-8 JSON array of turns with `id`, `role`, and optional `text`. Create `material-card.md` with `refresh_material_card()` after editorial material is prepared. If a bundle was deleted, rebuild it from all active-task turns; do not reuse deleted cursors or staged fallbacks.

`이번 작업은 저장하지 마` excludes the active task from archive, refresh, synthesis, and publication. `이 프로젝트 원고화 중지해줘` changes only the named registry entry to `paused`. These are on-demand actions: do not create timers, scheduled tasks, or background sync.

If thread reading, attachment handling, REST publication, or verification fails, preserve the last verified Vault state and report `failed` with the exact intended destination.
