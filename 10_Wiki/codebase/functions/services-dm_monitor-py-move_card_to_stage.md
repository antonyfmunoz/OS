---
type: codebase-function
file: services/dm_monitor.py
line: 104
generated: 2026-04-11
---

# move_card_to_stage

**File:** [[services-dm_monitor-py]] | **Line:** 104
**Signature:** `move_card_to_stage(username, from_stage, to_stage)`

Find the kanban card for username in from_stage and move it to to_stage.
Returns True if moved, False if not found or already in another stage.

## Calls

- [[services-dm_monitor-py-get_vault_path]]

## Called By

- [[services-dm_monitor-py-_advance_pipeline]]
