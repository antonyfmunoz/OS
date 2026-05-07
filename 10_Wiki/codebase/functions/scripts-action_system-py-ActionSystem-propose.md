---
type: codebase-function
file: scripts/action_system.py
line: 315
generated: 2026-05-07
---

# ActionSystem.propose

**File:** [[scripts-action_system-py]] | **Line:** 315
**Signature:** `propose() → Action`

**Class:** [[scripts-action_system-py-ActionSystem]]

Create an Action, populate impact + risk, but do NOT execute.

## Calls

- [[scripts-action_system-py-ActionSystem-_emit_log]]
- [[scripts-action_system-py-ActionSystem-assess_impact]]
- [[scripts-action_system-py-ActionSystem-evaluate_risk]]
- [[scripts-action_system-py-_new_id]]

## Called By

- [[scripts-action_system-py-main]]
- [[scripts-sandbox_safety_verifier-py-check_action_logs_tagged_with_env]]
- [[scripts-sandbox_safety_verifier-py-check_neon_audit_disabled_in_sandbox]]
- [[scripts-sandbox_safety_verifier-py-check_sandbox_edit_does_not_touch_production]]
- [[scripts-sandbox_smoke_test-py-step_edit_production_hub_in_sandbox]]
- [[scripts-sandbox_smoke_test-py-step_observability_env_views]]
- [[scripts-sandbox_smoke_test-py-step_write_file_in_sandbox]]
