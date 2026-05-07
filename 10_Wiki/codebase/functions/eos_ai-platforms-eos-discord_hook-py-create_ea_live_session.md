---
type: codebase-function
file: eos_ai/platforms/eos/discord_hook.py
line: 52
generated: 2026-05-07
---

# create_ea_live_session

**File:** [[eos_ai-platforms-eos-discord_hook-py]] | **Line:** 52
**Signature:** `create_ea_live_session(title) → Optional[str]`

Create a live session with EOS platform role participants.

Returns the live_session_id, or None on failure.
Participant roles are stored as their string values (platform-level,
not substrate slugs).

## Calls

- [[eos_ai-platforms-eos-discord_hook-py-_log]]
- [[eos_ai-platforms-eos-ea_orchestrator-py-_log]]
