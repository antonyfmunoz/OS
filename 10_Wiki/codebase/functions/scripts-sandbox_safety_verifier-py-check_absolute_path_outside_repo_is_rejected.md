---
type: codebase-function
file: scripts/sandbox_safety_verifier.py
line: 93
generated: 2026-04-12
---

# check_absolute_path_outside_repo_is_rejected

**File:** [[scripts-sandbox_safety_verifier-py]] | **Line:** 93
**Signature:** `check_absolute_path_outside_repo_is_rejected() → None`

/etc/passwd must never resolve in a sandbox env.

## Calls

- [[core-environment-py-Environment-cleanup]]
- [[core-environment-py-Environment-resolve]]
- [[core-environment-py-make_sandbox]]
