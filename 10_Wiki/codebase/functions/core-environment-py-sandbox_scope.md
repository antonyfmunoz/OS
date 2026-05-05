---
type: codebase-function
file: core/environment.py
line: 503
generated: 2026-04-12
---

# sandbox_scope

**File:** [[core-environment-py]] | **Line:** 503
**Signature:** `sandbox_scope() → Iterator[Environment]`

Context-manager wrapper around make_sandbox().

If cleanup_on_exit is True, the sandbox tree is removed on exit —
useful for one-shot verification runs. Default is to keep the tree
so the operator can inspect it afterward.

## Calls

- [[core-environment-py-Environment-cleanup]]
- [[core-environment-py-make_sandbox]]

## Decorators

- `@contextlib.contextmanager`
