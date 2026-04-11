---
type: codebase-function
file: core/action_system/logging.py
line: 49
generated: 2026-04-11
---

# log_decision

**File:** [[core-action_system-logging-py]] | **Line:** 49
**Signature:** `log_decision(context, options_considered, chosen_option, reasoning) → dict[str, Any]`

Append a decision record capturing WHY an action was (or was not) taken.

## Calls

- [[core-action_system-logging-py-_append_jsonl]]
- [[core-action_system-logging-py-_today_path]]

## Called By

- [[core-orchestrator-loop-py-_scan_failures]]
- [[core-orchestrator-loop-py-_scan_stale_deferred]]
- [[core-orchestrator-orchestrator-py-Orchestrator-run_workflow]]
- [[core-orchestrator-pipeline-py-run_pipeline]]
