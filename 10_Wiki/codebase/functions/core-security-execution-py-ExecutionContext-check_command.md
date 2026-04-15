---
type: codebase-function
file: core/security/execution.py
line: 157
generated: 2026-04-12
---

# ExecutionContext.check_command

**File:** [[core-security-execution-py]] | **Line:** 157
**Signature:** `check_command(command) → None`

**Class:** [[core-security-execution-py-ExecutionContext]]

Refuse shell metacharacters unless shell=True AND allow_shell=True.

## Called By

- [[core-security-execution-py-RestrictedExecutor-run]]
- [[scripts-security_smoke_test-py-test_execution]]
