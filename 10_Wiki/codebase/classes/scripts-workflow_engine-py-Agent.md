---
type: codebase-class
file: scripts/workflow_engine.py
line: 186
generated: 2026-04-12
---

# Agent

**File:** [[scripts-workflow_engine-py]] | **Line:** 186

A bounded capability unit that can execute a step.

capabilities     — set of StepType values this agent can run
allowed_actions  — set of ActionType values (only meaningful for EXECUTE)
memory_access    — "read" | "write" | "none"
...

## Methods

- [[scripts-workflow_engine-py-Agent-can_handle]]`(step) → tuple[bool, str]` — 

## Decorators

- `@dataclass`
