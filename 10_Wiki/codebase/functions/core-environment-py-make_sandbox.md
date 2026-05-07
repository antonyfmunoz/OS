---
type: codebase-function
file: core/environment.py
line: 403
generated: 2026-05-07
---

# make_sandbox

**File:** [[core-environment-py]] | **Line:** 403
**Signature:** `make_sandbox() → Environment`

Create a named sandbox environment under data/sandboxes/<name>/.

Args:
    name          — human-readable label; auto-generated if None.
    root          — override the tree location (tests use this).
...

## Calls

- [[core-environment-py-Environment-provision]]
- [[core-environment-py-_new_sandbox_name]]

## Called By

- [[core-environment-py-current_environment]]
- [[core-environment-py-sandbox_scope]]
- [[core-security-environments-py-env_for_name]]
- [[scripts-sandbox_runner-py-_resolve_env]]
- [[scripts-sandbox_safety_verifier-py-check_absolute_path_outside_repo_is_rejected]]
- [[scripts-sandbox_safety_verifier-py-check_action_logs_tagged_with_env]]
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
