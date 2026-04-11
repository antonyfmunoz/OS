---
type: codebase-function
file: core/orchestrator/pipeline.py
line: 200
generated: 2026-04-11
---

# run_pipeline

**File:** [[core-orchestrator-pipeline-py]] | **Line:** 200
**Signature:** `run_pipeline(pipeline, context) → PipelineResult`

Execute a pipeline sequentially.

Returns a PipelineResult with per-step outcomes. Every ActionStep
still passes through the full Control Plane, so idempotency,
validation, deferral, and logging behave exactly as they do for a
...

## Calls

- [[core-action_system-logging-py-log_decision]]
- [[core-orchestrator-pipeline-py-_run_action_step]]
- [[core-orchestrator-pipeline-py-_run_func_step]]
