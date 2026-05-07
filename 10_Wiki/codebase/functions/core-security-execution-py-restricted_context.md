---
type: codebase-function
file: core/security/execution.py
line: 298
generated: 2026-05-07
---

# restricted_context

**File:** [[core-security-execution-py]] | **Line:** 298
**Signature:** `restricted_context() → Iterator[ExecutionContext]`

Syntactic sugar for one-shot restricted execution.

Usage:
    with restricted_context(allowed_paths=["/tmp/scope"]) as ctx:
        RestrictedExecutor(ctx).run(["ls", "/tmp/scope"])

## Decorators

- `@contextmanager`
