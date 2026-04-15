---
type: codebase-function
file: scripts/sandbox_safety_verifier.py
line: 212
generated: 2026-04-12
---

# check_cleanup_refuses_random_directories

**File:** [[scripts-sandbox_safety_verifier-py]] | **Line:** 212
**Signature:** `check_cleanup_refuses_random_directories() → None`

env.cleanup() must refuse to delete anything not under the
sandbox/playground/tempdir roots.

## Calls

- [[core-environment-py-Environment-cleanup]]
