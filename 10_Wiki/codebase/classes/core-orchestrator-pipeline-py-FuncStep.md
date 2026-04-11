---
type: codebase-class
file: core/orchestrator/pipeline.py
line: 67
generated: 2026-04-11
---

# FuncStep

**File:** [[core-orchestrator-pipeline-py]] | **Line:** 67

A pipeline step that runs a plain Python callable.

The callable receives the shared `context` dict and must return a
dict. Convention: include an `"ok"` key so `stop_on_fail` can tell
success from failure uniformly with ActionStep results.
...

## Decorators

- `@dataclass`
