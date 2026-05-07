---
type: codebase-function
file: scripts/sandbox_safety_verifier.py
line: 79
generated: 2026-05-07
---

# check_guard_blocks_production_paths

**File:** [[scripts-sandbox_safety_verifier-py]] | **Line:** 79
**Signature:** `check_guard_blocks_production_paths() → None`

Environment.guard_write() must reject every forbidden prefix.

## Calls

- [[core-environment-py-Environment-cleanup]]
- [[core-environment-py-Environment-guard_write]]
- [[core-environment-py-make_sandbox]]
