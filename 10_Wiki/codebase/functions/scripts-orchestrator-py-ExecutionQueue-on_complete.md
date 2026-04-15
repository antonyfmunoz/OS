---
type: codebase-function
file: scripts/orchestrator.py
line: 391
generated: 2026-04-12
---

# ExecutionQueue.on_complete

**File:** [[scripts-orchestrator-py]] | **Line:** 391
**Signature:** `on_complete(handler) → None`

**Class:** [[scripts-orchestrator-py-ExecutionQueue]]

Register a callback fired after every run (success OR failure).

## Called By

- [[scripts-orchestrator-py-EventAgent-__init__]]
- [[scripts-orchestrator-py-RetryPolicy-__init__]]
