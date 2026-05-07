---
type: codebase-function
file: core/action_system/logging.py
line: 32
generated: 2026-05-07
---

# log_execution

**File:** [[core-action_system-logging-py]] | **Line:** 32
**Signature:** `log_execution(action, result) → str`

Append a full action record to today's execution log.

Returns the path written. `result` is optional — if omitted we use
whatever is on the action. This lets callers log at any lifecycle
transition (proposed, rejected, failed, executed) with one call.

## Calls

- [[core-action_system-logging-py-_append_jsonl]]
- [[core-action_system-logging-py-_today_path]]
