---
type: codebase-class
file: core/orchestrator/steps.py
line: 42
generated: 2026-05-07
---

# ScriptWorkflowSpec

**File:** [[core-orchestrator-steps-py]] | **Line:** 42

Declarative shape of a cron-invoked run_script workflow.

`idempotency_key` is a fully-formed string (not a template), so
callers can compute per-day or per-week keys with whatever logic
they need. `description_suffix` is appended to the base description
...

## Decorators

- `@dataclass`
