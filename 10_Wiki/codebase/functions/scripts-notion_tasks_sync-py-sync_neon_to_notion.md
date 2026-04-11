---
type: codebase-function
file: scripts/notion_tasks_sync.py
line: 188
generated: 2026-04-11
---

# sync_neon_to_notion

**File:** [[scripts-notion_tasks_sync-py]] | **Line:** 188
**Signature:** `sync_neon_to_notion() → int`

Push status changes from Neon back to Notion.
Finds dex_task events flagged with needs_notion_sync and syncs them back.

## Calls

- [[scripts-notion_tasks_sync-py-push_status_to_notion]]

## Called By

- [[scripts-notion_tasks_sync-py-run_sync]]
