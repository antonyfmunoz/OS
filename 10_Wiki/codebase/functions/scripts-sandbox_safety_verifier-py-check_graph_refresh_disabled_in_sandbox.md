---
type: codebase-function
file: scripts/sandbox_safety_verifier.py
line: 234
generated: 2026-05-07
---

# check_graph_refresh_disabled_in_sandbox

**File:** [[scripts-sandbox_safety_verifier-py]] | **Line:** 234
**Signature:** `check_graph_refresh_disabled_in_sandbox() → None`

_refresh_graph should return mode=skipped in sandbox mode.

## Calls

- [[core-environment-py-Environment-cleanup]]
- [[core-environment-py-make_sandbox]]
- [[scripts-action_system-py-ActionSystem-_refresh_graph]]
- [[scripts-sandbox_safety_verifier-py-_assert]]
- [[scripts-workflow_engine-py-AgentRegistry-get]]
