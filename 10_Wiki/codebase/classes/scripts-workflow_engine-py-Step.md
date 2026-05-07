---
type: codebase-class
file: scripts/workflow_engine.py
line: 108
generated: 2026-05-07
---

# Step

**File:** [[scripts-workflow_engine-py]] | **Line:** 108

A single unit of work in a workflow.

dependencies: list of step ids that must succeed before this step runs.
assigned_agent: name of a registered Agent (see AgentRegistry).
input: dict with step-type-specific keys. Common:
...

## Methods

- [[scripts-workflow_engine-py-Step-to_dict]]`() → dict[str, Any]` — 

## Decorators

- `@dataclass`
