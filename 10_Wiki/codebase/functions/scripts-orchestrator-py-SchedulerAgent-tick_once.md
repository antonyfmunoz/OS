---
type: codebase-function
file: scripts/orchestrator.py
line: 533
generated: 2026-04-12
---

# SchedulerAgent.tick_once

**File:** [[scripts-orchestrator-py]] | **Line:** 533
**Signature:** `tick_once() → int`

**Class:** [[scripts-orchestrator-py-SchedulerAgent]]

One pass over the registry. Returns the number of jobs submitted.

## Calls

- [[scripts-orchestrator-py-ActivityLog-emit]]
- [[scripts-orchestrator-py-ExecutionQueue-submit]]
- [[scripts-orchestrator-py-Orchestrator-jobs]]
- [[scripts-orchestrator-py-Orchestrator-submit]]
- [[scripts-orchestrator-py-_parse_hhmm]]
- [[scripts-workflow_engine-py-AgentRegistry-get]]

## Called By

- [[core-control_plane-py-_cmd_start]]
- [[scripts-orchestrator-py-SchedulerAgent-_loop]]
- [[scripts-orchestrator-py-_cmd_start]]
