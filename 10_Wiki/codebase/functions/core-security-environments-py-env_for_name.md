---
type: codebase-function
file: core/security/environments.py
line: 171
generated: 2026-04-12
---

# env_for_name

**File:** [[core-security-environments-py]] | **Line:** 171
**Signature:** `env_for_name(name) → SecurityEnv`

Resolve a tier name into a SecurityEnv.

Accepted names:
    "prod" | "production"   → production
    "sandbox" | "sbx"       → persistent sandbox
...

## Calls

- [[core-environment-py-Environment-production]]
- [[core-environment-py-make_playground]]
- [[core-environment-py-make_sandbox]]
- [[core-security-environments-py-_canon_tier]]

## Called By

- [[core-security-cli-py-cmd_env_show]]
- [[scripts-security_smoke_test-py-test_action_system_integration]]
- [[scripts-security_smoke_test-py-test_security_context]]
