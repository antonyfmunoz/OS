---
type: codebase-function
file: core/environment.py
line: 255
generated: 2026-04-12
---

# Environment.read_file

**File:** [[core-environment-py]] | **Line:** 255
**Signature:** `read_file(target) → bytes`

**Class:** [[core-environment-py-Environment]]

Read with read-through: if the file isn't in the workspace,
fall back to the production tree.

Production env: just reads the file.
Sandbox env: prefers workspace, falls back to production.
...

## Calls

- [[core-environment-py-Environment-_to_rel]]
- [[core-environment-py-Environment-resolve]]
