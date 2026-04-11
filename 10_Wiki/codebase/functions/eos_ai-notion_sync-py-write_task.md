---
type: codebase-function
file: eos_ai/notion_sync.py
line: 132
generated: 2026-04-11
---

# write_task

**File:** [[eos_ai-notion_sync-py]] | **Line:** 132
**Signature:** `write_task(venture_id, name, status, priority, department, assigned_to, assignee_type, source, task_type, due_date, neon_id, notes, requires_approval) → str`

Create a task row. Returns Notion page ID or ''.

## Calls

- [[eos_ai-notion_sync-py-_checkbox]]
- [[eos_ai-notion_sync-py-_create_page]]
- [[eos_ai-notion_sync-py-_date]]
- [[eos_ai-notion_sync-py-_select]]
- [[eos_ai-notion_sync-py-_text]]
- [[eos_ai-notion_sync-py-_title]]
- [[eos_ai-notion_sync-py-get_db_id]]

## Called By

- [[eos_ai-notion_sync-py-push_pending_tasks_to_notion]]
