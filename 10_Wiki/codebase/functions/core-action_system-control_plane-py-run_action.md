---
type: codebase-function
file: core/action_system/control_plane.py
line: 83
generated: 2026-04-12
---

# run_action

**File:** [[core-action_system-control_plane-py]] | **Line:** 83
**Signature:** `run_action(type, description) → Action`

Push an action through the full Control Plane lifecycle.

Returns the Action object with final state in `.status`, `.validation`,
`.approval`, and `.result`. Every transition is persisted to
/opt/OS/logs/execution/.
...

## Calls

- [[core-action_system-control_plane-py-_deferred_file_exists]]
- [[core-action_system-control_plane-py-_execute_approved]]
- [[core-action_system-control_plane-py-_skipped_duplicate]]

## Called By

- [[core-orchestrator-handlers-py-handle_action_retry_requested]]
- [[core-orchestrator-pipeline-py-_run_action_step]]
- [[core-orchestrator-steps-py-run_script_workflow]]
- [[core-tool_mastery_manager-ensure-py-_queue]]
- [[scripts-control_plane_run-py-main]]
- [[scripts-force_execution_loop-py-step_generate_outreach_message]]
- [[scripts-force_execution_loop-py-step_save_outreach_to_file]]
- [[scripts-force_execution_loop-py-step_verify_output]]
