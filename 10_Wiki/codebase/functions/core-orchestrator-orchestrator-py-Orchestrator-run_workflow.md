---
type: codebase-function
file: core/orchestrator/orchestrator.py
line: 73
generated: 2026-04-11
---

# Orchestrator.run_workflow

**File:** [[core-orchestrator-orchestrator-py]] | **Line:** 73
**Signature:** `run_workflow(name, context) → dict[str, Any]`

**Class:** [[core-orchestrator-orchestrator-py-Orchestrator]]

Run a registered workflow by name.

Returns a dict with keys:
  - name, ok, status, duration_s, result

...

## Calls

- [[core-action_system-logging-py-log_decision]]
- [[core-orchestrator-orchestrator-py-Orchestrator-_record_run]]
