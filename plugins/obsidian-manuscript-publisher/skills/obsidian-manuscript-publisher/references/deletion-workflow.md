# Deletion Workflow

Use this reference only for `이 대화의 옵시디언 자료를 전부 삭제해줘` or `이 대화 옵시디언 폴더를 지워줘`.

The explicit request approves deletion of the active conversation bundle only. Read the active task/thread ID and use it as the exact `conversation_key`; never infer a target from title, topic, or similar material.

Run `scripts/delete_conversation_bundle.py` with the runtime Local REST configuration, exact registered `00 Conversations` root, exact key, and Vault root. The script lists only that bundle, checks `metadata.json`, deletes files through REST deepest-first, requires 404 readback, and verifies an unrelated sibling remains byte-identical.

Remove empty directories only after REST file deletion succeeds, and only with `rmdir` on the verified-empty exact child. Refuse cleanup for remaining files, symbolic links, or normalized paths outside the exact root. Report `deleted`, `already_absent`, or `partial_delete_failed` with remaining paths. Never delete an independent versioned manuscript or use direct filesystem deletion for Vault files.
