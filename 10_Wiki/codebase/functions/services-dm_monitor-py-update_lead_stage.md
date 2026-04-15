---
type: codebase-function
file: services/dm_monitor.py
line: 165
generated: 2026-04-12
---

# update_lead_stage

**File:** [[services-dm_monitor-py]] | **Line:** 165
**Signature:** `update_lead_stage(username, new_stage, conversation_stage)`

Update kanban_stage, status, conversation_stage, and last_stage_update in the lead's frontmatter.

## Calls

- [[services-dm_monitor-py-get_vault_path]]

## Called By

- [[services-dm_monitor-py-_advance_pipeline]]
