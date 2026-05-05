---
type: codebase-function
file: core/security/execution.py
line: 121
generated: 2026-04-12
---

# ExecutionContext.check_path

**File:** [[core-security-execution-py]] | **Line:** 121
**Signature:** `check_path(path) → Path`

**Class:** [[core-security-execution-py-ExecutionContext]]

Raise ExecutionDenied if `path` is not allowed for `mode`.

Returns the resolved absolute Path on success.

## Calls

- [[core-security-execution-py-ExecutionContext-_matches]]

## Called By

- [[core-security-execution-py-ExecutionContext-may_path]]
- [[core-security-execution-py-RestrictedExecutor-run]]
- [[scripts-security_smoke_test-py-test_execution]]
