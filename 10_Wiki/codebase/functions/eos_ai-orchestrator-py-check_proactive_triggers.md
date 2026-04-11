---
type: codebase-function
file: eos_ai/orchestrator.py
line: 884
generated: 2026-04-11
---

# check_proactive_triggers

**File:** [[eos_ai-orchestrator-py]] | **Line:** 884
**Signature:** `check_proactive_triggers(ctx) → list[str]`

Runs after morning cycle. Checks conditions that warrant unsolicited
Telegram alerts. Returns list of alert messages (empty = nothing to surface).

## Calls

- [[eos_ai-db-py-get_conn]]

## Called By

- [[eos_ai-orchestrator-py-run_full_morning_cycle]]
