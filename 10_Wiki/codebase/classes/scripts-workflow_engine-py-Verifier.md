---
type: codebase-class
file: scripts/workflow_engine.py
line: 306
generated: 2026-04-12
---

# Verifier

**File:** [[scripts-workflow_engine-py]] | **Line:** 306

Pre-flight and post-flight safety checks.

Pre-flight (validate_workflow):
  - IDs unique, dependencies point to real steps, DAG (no cycles)
  - every assigned agent can handle its step
...

## Methods

- [[scripts-workflow_engine-py-Verifier-__init__]]`(registry) → None` — 
- [[scripts-workflow_engine-py-Verifier-validate_workflow]]`(wf) → list[str]` — 
- [[scripts-workflow_engine-py-Verifier-verify_step_output]]`(step) → tuple[bool, str]` — 
