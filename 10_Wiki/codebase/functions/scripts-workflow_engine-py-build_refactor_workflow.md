---
type: codebase-function
file: scripts/workflow_engine.py
line: 1052
generated: 2026-04-12
---

# build_refactor_workflow

**File:** [[scripts-workflow_engine-py]] | **Line:** 1052
**Signature:** `build_refactor_workflow(goal, target_file) → Workflow`

Code refactor: inspect graph → plan change → propose edit (dry-run safe).

The EXECUTE step uses action_type=query_graph (risk=NONE) so the whole
workflow can run without --approve. A real refactor would add EDIT_FILE
steps behind an approval gate.

## Calls

- [[scripts-workflow_engine-py-_new_id]]

## Called By

- [[scripts-orchestrator-py-build_default_jobs]]
