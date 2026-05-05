---
type: codebase-function
file: core/environment.py
line: 187
generated: 2026-04-12
---

# Environment.resolve

**File:** [[core-environment-py]] | **Line:** 187
**Signature:** `resolve(target) → Path`

**Class:** [[core-environment-py-Environment]]

Translate a repo-relative or absolute path into this env's tree.

Rules:
  * Production: resolves against the real repo root.
  * Sandbox/playground: always resolves inside `self.workspace`,
...

## Calls

- [[core-environment-py-Environment-_to_rel]]

## Called By

- [[core-environment-py-Environment-cleanup]]
- [[core-environment-py-Environment-ensure_copied]]
- [[core-environment-py-Environment-guard_write]]
- [[core-environment-py-Environment-read_file]]
- [[core-security-environments-py-SecurityEnv-resolve]]
- [[scripts-action_system-py-_abs]]
- [[scripts-sandbox_safety_verifier-py-check_absolute_path_outside_repo_is_rejected]]
