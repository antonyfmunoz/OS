---
type: codebase-function
file: eos_ai/notion_sync.py
line: 222
generated: 2026-04-12
---

# write_metric

**File:** [[eos_ai-notion_sync-py]] | **Line:** 222
**Signature:** `write_metric(venture_id, metric_name, value, target, unit, period, category, department, linked_goal, notes) → str`

Create a metric/KPI row. Returns page ID or ''.

## Calls

- [[eos_ai-notion_sync-py-_create_page]]
- [[eos_ai-notion_sync-py-_date]]
- [[eos_ai-notion_sync-py-_number]]
- [[eos_ai-notion_sync-py-_select]]
- [[eos_ai-notion_sync-py-_text]]
- [[eos_ai-notion_sync-py-_title]]
- [[eos_ai-notion_sync-py-get_db_id]]

## Called By

- [[scripts-notion_seed_all-py-seed_empyrean]]
- [[scripts-notion_seed_all-py-seed_personal_brand]]
