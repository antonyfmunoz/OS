---
type: codebase-function
file: core/security/environments.py
line: 198
generated: 2026-05-07
---

# wrap_environment

**File:** [[core-security-environments-py]] | **Line:** 198
**Signature:** `wrap_environment(env) → SecurityEnv`

Take an existing core.environment.Environment and wrap it with
the matching policy. Useful when the caller already has an env
object (e.g., ActionSystem.env) and just needs the security view.
