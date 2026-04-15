---
type: codebase-function
file: scripts/action_system.py
line: 448
generated: 2026-04-12
---

# ActionSystem.execute

**File:** [[scripts-action_system-py]] | **Line:** 448
**Signature:** `execute(action) → ActionResult`

**Class:** [[scripts-action_system-py-ActionSystem]]

Run the approval gate, then dispatch to the type-specific
executor. Always logs the outcome — success or failure.

## Calls

- [[scripts-action_system-py-ActionSystem-_advisor_check]]
- [[scripts-action_system-py-ActionSystem-_emit_log]]
- [[scripts-action_system-py-ActionSystem-_exec_delete_file]]
- [[scripts-action_system-py-ActionSystem-_exec_edit_file]]
- [[scripts-action_system-py-ActionSystem-_exec_query_graph]]
- [[scripts-action_system-py-ActionSystem-_exec_run_command]]
- [[scripts-action_system-py-ActionSystem-_exec_run_script]]
- [[scripts-action_system-py-ActionSystem-_exec_write_file]]
- [[scripts-action_system-py-ActionSystem-_preview]]
- [[scripts-action_system-py-ActionSystem-_refresh_graph]]
- [[scripts-action_system-py-ActionSystem-_security_check]]

## Called By

- [[scripts-action_system-py-main]]
- [[scripts-sandbox_safety_verifier-py-check_action_logs_tagged_with_env]]
- [[scripts-sandbox_safety_verifier-py-check_neon_audit_disabled_in_sandbox]]
- [[scripts-sandbox_safety_verifier-py-check_sandbox_edit_does_not_touch_production]]
- [[scripts-sandbox_smoke_test-py-step_edit_production_hub_in_sandbox]]
- [[scripts-sandbox_smoke_test-py-step_observability_env_views]]
- [[scripts-sandbox_smoke_test-py-step_write_file_in_sandbox]]
