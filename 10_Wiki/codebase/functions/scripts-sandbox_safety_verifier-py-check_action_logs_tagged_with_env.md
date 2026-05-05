---
type: codebase-function
file: scripts/sandbox_safety_verifier.py
line: 185
generated: 2026-04-12
---

# check_action_logs_tagged_with_env

**File:** [[scripts-sandbox_safety_verifier-py]] | **Line:** 185
**Signature:** `check_action_logs_tagged_with_env() → None`

Every action log row written from a sandbox must carry env=label.

## Calls

- [[core-environment-py-Environment-cleanup]]
- [[core-environment-py-make_sandbox]]
- [[scripts-action_system-py-ActionSystem-execute]]
- [[scripts-action_system-py-ActionSystem-propose]]
- [[scripts-sandbox_safety_verifier-py-_assert]]
- [[scripts-workflow_engine-py-AgentRegistry-get]]
