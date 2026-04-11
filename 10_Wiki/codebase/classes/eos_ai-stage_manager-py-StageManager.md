---
type: codebase-class
file: eos_ai/stage_manager.py
line: 100
generated: 2026-04-11
---

# StageManager

**File:** [[eos_ai-stage_manager-py]] | **Line:** 100

*No docstring.*

## Methods

- [[eos_ai-stage_manager-py-StageManager-__init__]]`(ctx)` — 
- [[eos_ai-stage_manager-py-StageManager-advance_stage]]`(venture_id, new_stage) → StageTransitionResult` — Handle full stage transition. Updates BIS, Notion, fires Discord event.
- [[eos_ai-stage_manager-py-StageManager-_update_notion]]`(venture_id, new_stage, unlocked, previous_stage) → None` — Update Notion Stage Guidance and Morning Brief pages.
- [[eos_ai-stage_manager-py-StageManager-_fire_discord_event]]`(venture_id, new_stage, unlocked) → None` — Log stage transition event to Neon for Discord bot to surface.
