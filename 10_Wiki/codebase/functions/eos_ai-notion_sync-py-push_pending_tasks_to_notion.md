---
type: codebase-function
file: eos_ai/notion_sync.py
line: 371
generated: 2026-04-12
---

# push_pending_tasks_to_notion

**File:** [[eos_ai-notion_sync-py]] | **Line:** 371
**Signature:** `push_pending_tasks_to_notion(venture_id, ctx) → int`

Push tasks from Neon to Notion that don't have a notion_page_id yet.
Returns count of tasks pushed.

## Calls

- [[eos_ai-notion_sync-py-get_db_id]]
- [[eos_ai-notion_sync-py-write_task]]

## Called By

- [[eos_ai-notion_sync-py-push_all_ventures]]
