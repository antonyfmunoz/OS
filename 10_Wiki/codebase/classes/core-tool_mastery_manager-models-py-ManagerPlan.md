---
type: codebase-class
file: core/tool_mastery_manager/models.py
line: 79
generated: 2026-04-11
---

# ManagerPlan

**File:** [[core-tool_mastery_manager-models-py]] | **Line:** 79

Planned Control Plane action for a non-READY tool.

The Manager never invokes action types outside the Control Plane's
allowed set. Research / refresh / repair are encoded as medium-risk
`run_script` actions targeting the research dispatcher, with the
...

## Methods

- [[core-tool_mastery_manager-models-py-ManagerPlan-to_dict]]`() → dict[str, Any]` — 

## Decorators

- `@dataclass`
