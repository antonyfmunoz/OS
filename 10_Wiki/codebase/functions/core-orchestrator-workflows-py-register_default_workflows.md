---
type: codebase-function
file: core/orchestrator/workflows.py
line: 79
generated: 2026-05-07
---

# register_default_workflows

**File:** [[core-orchestrator-workflows-py]] | **Line:** 79
**Signature:** `register_default_workflows(orch) → list[str]`

Register all known CP workflows on the given (or default) orchestrator.

Returns the list of registered workflow names. Safe to call repeatedly.

## Calls

- [[core-orchestrator-workflows-py-_wrap_main]]

## Called By

- [[scripts-orchestrator_loop-py-main]]
- [[scripts-orchestrator_status-py-recent_workflows]]
