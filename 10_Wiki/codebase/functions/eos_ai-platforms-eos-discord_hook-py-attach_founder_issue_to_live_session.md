---
type: codebase-function
file: eos_ai/platforms/eos/discord_hook.py
line: 104
generated: 2026-05-07
---

# attach_founder_issue_to_live_session

**File:** [[eos_ai-platforms-eos-discord_hook-py]] | **Line:** 104
**Signature:** `attach_founder_issue_to_live_session(live_session_id, issue_text) → Optional[str]`

Attach a founder issue to a live session by creating a substrate task
and linking it to the session.

Returns the created task_id, or None on failure.

## Calls

- [[eos_ai-platforms-eos-discord_hook-py-_log]]
- [[eos_ai-platforms-eos-ea_orchestrator-py-_log]]
