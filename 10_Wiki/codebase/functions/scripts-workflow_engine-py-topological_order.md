---
type: codebase-function
file: scripts/workflow_engine.py
line: 375
generated: 2026-04-12
---

# topological_order

**File:** [[scripts-workflow_engine-py]] | **Line:** 375
**Signature:** `topological_order(steps) → list[str]`

Kahn's algorithm. Returns step ids in a valid execution order.

Raises ValueError("cycle detected: ...") if the dependency graph is not
a DAG. We want to fail early, not halfway through a workflow.

## Called By

- [[scripts-workflow_engine-py-Verifier-validate_workflow]]
- [[scripts-workflow_engine-py-WorkflowEngine-run_workflow]]
