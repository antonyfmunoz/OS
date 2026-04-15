---
type: codebase-function
file: core/security/execution.py
line: 180
generated: 2026-04-12
---

# ExecutionContext.scrubbed_env

**File:** [[core-security-execution-py]] | **Line:** 180
**Signature:** `scrubbed_env(extra) → dict`

**Class:** [[core-security-execution-py-ExecutionContext]]

Return a minimized env dict to hand to subprocess.

## Called By

- [[core-security-execution-py-RestrictedExecutor-run]]
