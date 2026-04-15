---
type: codebase-function
file: eos_ai/orchestrator.py
line: 962
generated: 2026-04-12
---

# check_outcome_milestone

**File:** [[eos_ai-orchestrator-py]] | **Line:** 962
**Signature:** `check_outcome_milestone(ctx, new_outcome_count) → None`

Event-driven milestone check called immediately when a new outcome is logged.
Sends Telegram alert without waiting for 6am cycle.

## Calls

- [[eos_ai-orchestrator-py-_notify]]
