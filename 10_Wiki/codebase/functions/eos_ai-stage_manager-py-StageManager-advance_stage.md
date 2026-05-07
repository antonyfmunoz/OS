---
type: codebase-function
file: eos_ai/stage_manager.py
line: 105
generated: 2026-05-07
---

# StageManager.advance_stage

**File:** [[eos_ai-stage_manager-py]] | **Line:** 105
**Signature:** `advance_stage(venture_id, new_stage) → StageTransitionResult`

**Class:** [[eos_ai-stage_manager-py-StageManager]]

Handle full stage transition. Updates BIS, Notion, fires Discord event.
Synchronous — safe to call from gateway.py.

## Calls

- [[eos_ai-stage_manager-py-StageManager-_fire_discord_event]]
- [[eos_ai-stage_manager-py-StageManager-_update_notion]]
