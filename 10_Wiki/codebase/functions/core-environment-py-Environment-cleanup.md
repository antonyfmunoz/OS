---
type: codebase-function
file: core/environment.py
line: 324
generated: 2026-04-12
---

# Environment.cleanup

**File:** [[core-environment-py]] | **Line:** 324
**Signature:** `cleanup() → None`

**Class:** [[core-environment-py-Environment]]

Remove the entire env tree. No-op for production.

Only call on ephemeral envs or sandboxes you explicitly want gone.
This is destructive — but it only ever touches the sandbox tree.

## Calls

- [[core-environment-py-Environment-resolve]]

## Called By

- [[core-environment-py-Environment-__exit__]]
- [[core-environment-py-sandbox_scope]]
- [[scripts-sandbox_runner-py-_cmd_clean]]
- [[scripts-sandbox_runner-py-_cmd_playground]]
- [[scripts-sandbox_safety_verifier-py-check_absolute_path_outside_repo_is_rejected]]
- [[scripts-sandbox_safety_verifier-py-check_action_logs_tagged_with_env]]
- [[scripts-sandbox_safety_verifier-py-check_cleanup_refuses_random_directories]]
- [[scripts-sandbox_safety_verifier-py-check_graph_refresh_disabled_in_sandbox]]
- [[scripts-sandbox_safety_verifier-py-check_guard_blocks_production_paths]]
- [[scripts-sandbox_safety_verifier-py-check_neon_audit_disabled_in_sandbox]]
- [[scripts-sandbox_safety_verifier-py-check_sandbox_edit_does_not_touch_production]]
- [[scripts-sandbox_safety_verifier-py-check_sandbox_write_blocked_if_target_outside_workspace]]
- [[scripts-sandbox_safety_verifier-py-check_workflow_logs_land_in_sandbox]]
- [[scripts-sandbox_smoke_test-py-step_edit_production_hub_in_sandbox]]
- [[scripts-sandbox_smoke_test-py-step_observability_env_views]]
- [[scripts-sandbox_smoke_test-py-step_workflow_logs_isolated]]
- [[scripts-sandbox_smoke_test-py-step_write_file_in_sandbox]]
