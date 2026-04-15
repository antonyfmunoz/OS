---
type: codebase-function
file: core/environment.py
line: 477
generated: 2026-04-12
---

# current_environment

**File:** [[core-environment-py]] | **Line:** 477
**Signature:** `current_environment() → Environment`

Return the env selected via the EOS_ENV environment variable.

Values:
  unset | "production" | "prod" → production environment
  "sandbox:<name>"               → named sandbox (created if missing)
...

## Calls

- [[core-environment-py-Environment-production]]
- [[core-environment-py-make_playground]]
- [[core-environment-py-make_sandbox]]
