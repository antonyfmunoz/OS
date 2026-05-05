---
type: codebase-function
file: scripts/workflow_engine.py
line: 739
generated: 2026-04-12
---

# WorkflowEngine.run_workflow

**File:** [[scripts-workflow_engine-py]] | **Line:** 739
**Signature:** `run_workflow(wf) → dict`

**Class:** [[scripts-workflow_engine-py-WorkflowEngine]]

*No docstring.*

## Calls

- [[scripts-workflow_engine-py-Verifier-validate_workflow]]
- [[scripts-workflow_engine-py-Workflow-step]]
- [[scripts-workflow_engine-py-WorkflowEngine-_aggregate]]
- [[scripts-workflow_engine-py-WorkflowEngine-_emit]]
- [[scripts-workflow_engine-py-WorkflowEngine-_finalize]]
- [[scripts-workflow_engine-py-WorkflowEngine-_log_to_memory]]
- [[scripts-workflow_engine-py-WorkflowEngine-_run_step_with_retry]]
- [[scripts-workflow_engine-py-WorkflowEngine-_save_state]]
- [[scripts-workflow_engine-py-topological_order]]

## Called By

- [[scripts-orchestrator-py-ExecutionQueue-_run_job]]
- [[scripts-sandbox_safety_verifier-py-check_workflow_logs_land_in_sandbox]]
- [[scripts-sandbox_smoke_test-py-step_workflow_logs_isolated]]
- [[scripts-workflow_engine-py-main]]
