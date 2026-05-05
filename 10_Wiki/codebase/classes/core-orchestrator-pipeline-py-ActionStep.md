---
type: codebase-class
file: core/orchestrator/pipeline.py
line: 42
generated: 2026-04-12
---

# ActionStep

**File:** [[core-orchestrator-pipeline-py]] | **Line:** 42

A pipeline step that dispatches through `run_action()`.

All keyword arguments map 1:1 to `run_action()` parameters. The
`inputs_fn` hook lets a step derive its inputs from the running
context — useful when step N depends on output from step N-1.

## Decorators

- `@dataclass`
