---
type: codebase-function
file: scripts/orchestrator.py
line: 905
generated: 2026-05-07
---

# build_default_jobs

**File:** [[scripts-orchestrator-py]] | **Line:** 905
**Signature:** `build_default_jobs() → list[Job]`

The three example workflows from the spec, wired into orchestration.

## Calls

- [[scripts-workflow_engine-py-build_content_workflow]]
- [[scripts-workflow_engine-py-build_refactor_workflow]]
- [[scripts-workflow_engine-py-build_research_workflow]]

## Called By

- [[core-control_plane-py-ControlPlane-__init__]]
- [[scripts-orchestrator-py-_cmd_list]]
- [[scripts-orchestrator-py-_cmd_start]]
- [[scripts-orchestrator-py-_cmd_trigger]]
