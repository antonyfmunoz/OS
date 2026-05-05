---
type: codebase-function
file: scripts/sandbox_safety_verifier.py
line: 159
generated: 2026-04-12
---

# check_workflow_logs_land_in_sandbox

**File:** [[scripts-sandbox_safety_verifier-py]] | **Line:** 159
**Signature:** `check_workflow_logs_land_in_sandbox() → None`

Run a dry-run workflow in a sandbox and assert the sandbox log
grew while the production log did not.

## Calls

- [[core-environment-py-Environment-cleanup]]
- [[core-environment-py-make_sandbox]]
- [[scripts-sandbox_safety_verifier-py-_assert]]
- [[scripts-workflow_engine-py-AgentRegistry-get]]
- [[scripts-workflow_engine-py-WorkflowEngine-run_workflow]]
- [[scripts-workflow_engine-py-build_research_workflow]]
