---
type: codebase-function
file: core/environment.py
line: 440
generated: 2026-04-12
---

# make_playground

**File:** [[core-environment-py]] | **Line:** 440
**Signature:** `make_playground() → Environment`

Create a lightweight, ephemeral playground environment.

Playgrounds:
  * live under data/playgrounds/<name>/ (or a tempdir if `root` is set)
  * auto-clean up on `with` exit
...

## Calls

- [[core-environment-py-Environment-provision]]
- [[core-environment-py-_new_sandbox_name]]

## Called By

- [[core-environment-py-current_environment]]
- [[core-security-environments-py-env_for_name]]
- [[scripts-sandbox_runner-py-_cmd_playground]]
- [[scripts-sandbox_runner-py-_resolve_env]]
- [[scripts-sandbox_safety_verifier-py-check_playground_is_ephemeral]]
- [[scripts-sandbox_smoke_test-py-step_playground_is_ephemeral]]
