---
type: codebase-function
file: scripts/workflow_engine.py
line: 462
generated: 2026-04-12
---

# StepExecutor.run

**File:** [[scripts-workflow_engine-py]] | **Line:** 462
**Signature:** `run(step, context) → dict`

**Class:** [[scripts-workflow_engine-py-StepExecutor]]

*No docstring.*

## Calls

- [[scripts-workflow_engine-py-Agent-can_handle]]
- [[scripts-workflow_engine-py-AgentRegistry-get]]
- [[scripts-workflow_engine-py-StepExecutor-_apply_advisor]]
- [[scripts-workflow_engine-py-StepExecutor-_expand_prompt]]
- [[scripts-workflow_engine-py-StepExecutor-_run_decision]]
- [[scripts-workflow_engine-py-StepExecutor-_run_execute]]
- [[scripts-workflow_engine-py-StepExecutor-_run_research]]
- [[scripts-workflow_engine-py-StepExecutor-_run_write]]
- [[scripts-workflow_engine-py-StepExecutor-_should_use_advisor]]

## Called By

- [[scripts-sandbox_smoke_test-py-step_orchestrator_tick_in_sandbox]]
- [[scripts-sandbox_smoke_test-py-step_run_safety_verifier]]
- [[scripts-workflow_engine-py-WorkflowEngine-_run_step_with_retry]]
