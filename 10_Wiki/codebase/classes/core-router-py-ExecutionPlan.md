---
type: codebase-class
file: core/router.py
line: 68
generated: 2026-05-07
---

# ExecutionPlan

**File:** [[core-router-py]] | **Line:** 68

The output of route_execution() — a fully routed pipeline.

Each step has an assigned capability and fallback chain.
The plan includes the primitive trace and routing metadata.

## Methods

- [[core-router-py-ExecutionPlan-is_hybrid]]`() → bool` — True if different steps use different capability types.
- [[core-router-py-ExecutionPlan-to_dict]]`() → dict[str, Any]` — 

## Decorators

- `@dataclass`
