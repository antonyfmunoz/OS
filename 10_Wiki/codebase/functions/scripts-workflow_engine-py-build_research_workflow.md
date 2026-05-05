---
type: codebase-function
file: scripts/workflow_engine.py
line: 963
generated: 2026-04-12
---

# build_research_workflow

**File:** [[scripts-workflow_engine-py]] | **Line:** 963
**Signature:** `build_research_workflow(goal) → Workflow`

Research a topic: graph-scan → summarize → classify confidence.

## Calls

- [[scripts-workflow_engine-py-_new_id]]

## Called By

- [[scripts-orchestrator-py-build_default_jobs]]
- [[scripts-sandbox_safety_verifier-py-check_workflow_logs_land_in_sandbox]]
- [[scripts-sandbox_smoke_test-py-step_workflow_logs_isolated]]
