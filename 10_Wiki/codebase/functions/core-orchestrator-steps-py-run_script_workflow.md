---
type: codebase-function
file: core/orchestrator/steps.py
line: 64
generated: 2026-04-12
---

# run_script_workflow

**File:** [[core-orchestrator-steps-py]] | **Line:** 64
**Signature:** `run_script_workflow(spec) → int`

Run a declarative run_script workflow through the Control Plane.

Returns the exit code the `_cp.py` wrapper should return:
  - 0 on executed, validated (deferred), or skipped_duplicate
  - 1 on any other status
...

## Calls

- [[core-action_system-control_plane-py-run_action]]

## Called By

- [[scripts-scheduled-morning_prep_cp-py-main]]
- [[scripts-scheduled-nightly_consolidation_cp-py-main]]
- [[scripts-scheduled-weekly_review_cp-py-main]]
