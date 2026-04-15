---
type: codebase-function
file: scripts/workflow_engine.py
line: 292
generated: 2026-04-12
---

# AgentRegistry.get

**File:** [[scripts-workflow_engine-py]] | **Line:** 292
**Signature:** `get(name) → Agent`

**Class:** [[scripts-workflow_engine-py-AgentRegistry]]

*No docstring.*

## Called By

- [[scripts-orchestrator-py-ActivityLog-emit]]
- [[scripts-orchestrator-py-ActivityLog-persist_to_memory]]
- [[scripts-orchestrator-py-EventAgent-_dispatch_fs_event]]
- [[scripts-orchestrator-py-EventAgent-_on_workflow_complete]]
- [[scripts-orchestrator-py-ExecutionQueue-_dispatch_loop]]
- [[scripts-orchestrator-py-ExecutionQueue-_run_job]]
- [[scripts-orchestrator-py-Orchestrator-trigger]]
- [[scripts-orchestrator-py-RetryPolicy-_handle]]
- [[scripts-orchestrator-py-SchedulerAgent-tick_once]]
- [[scripts-orchestrator-py-_cmd_trigger]]
- [[scripts-sandbox_safety_verifier-py-check_action_logs_tagged_with_env]]
- [[scripts-sandbox_safety_verifier-py-check_graph_refresh_disabled_in_sandbox]]
- [[scripts-sandbox_safety_verifier-py-check_workflow_logs_land_in_sandbox]]
- [[scripts-sandbox_smoke_test-py-step_observability_env_views]]
- [[scripts-sandbox_smoke_test-py-step_workflow_logs_isolated]]
- [[scripts-workflow_engine-py-Agent-can_handle]]
- [[scripts-workflow_engine-py-StepExecutor-_apply_advisor]]
- [[scripts-workflow_engine-py-StepExecutor-_run_decision]]
- [[scripts-workflow_engine-py-StepExecutor-_run_execute]]
- [[scripts-workflow_engine-py-StepExecutor-_run_research]]
