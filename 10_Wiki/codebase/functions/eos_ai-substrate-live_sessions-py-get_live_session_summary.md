---
type: codebase-function
file: eos_ai/substrate/live_sessions.py
line: 572
generated: 2026-05-07
---

# get_live_session_summary

**File:** [[eos_ai-substrate-live_sessions-py]] | **Line:** 572
**Signature:** `get_live_session_summary() → dict`

Get summary suitable for open_day/close_day integration.

Returns:
    {
        "active_live_sessions": int,
...

## Calls

- [[eos_ai-substrate-live_sessions-py-LiveSession-is_terminal]]
- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-all]]
- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-default]]
