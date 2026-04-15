---
type: codebase-class
file: scripts/orchestrator.py
line: 115
generated: 2026-04-12
---

# Job

**File:** [[scripts-orchestrator-py]] | **Line:** 115

One registered workflow + how/when it should run.

Only ONE of (interval_sec, at_time, event_pattern) should be set for a
given trigger_type. Validated by Verifier.validate_job().

...

## Methods

- [[scripts-orchestrator-py-Job-key]]`() → str` — 
- [[scripts-orchestrator-py-Job-to_public]]`() → dict[str, Any]` — Serializable view — drops callables.

## Decorators

- `@dataclass`
