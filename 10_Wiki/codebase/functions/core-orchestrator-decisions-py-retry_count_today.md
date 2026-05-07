---
type: codebase-function
file: core/orchestrator/decisions.py
line: 52
generated: 2026-05-07
---

# retry_count_today

**File:** [[core-orchestrator-decisions-py]] | **Line:** 52
**Signature:** `retry_count_today(action_id) → int`

How many retry decisions have been logged against this action today.

Counts any decision whose `context` is `orchestrator.loop.retry`
OR `orchestrator.handler.retry` and whose `related_action_id`
matches. Returns 0 if the log is missing.

## Calls

- [[core-orchestrator-decisions-py-_today_decision_log_path]]

## Called By

- [[core-orchestrator-decisions-py-should_retry]]
