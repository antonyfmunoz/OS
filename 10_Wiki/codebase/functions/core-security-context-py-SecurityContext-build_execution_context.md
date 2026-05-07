---
type: codebase-function
file: core/security/context.py
line: 469
generated: 2026-05-07
---

# SecurityContext.build_execution_context

**File:** [[core-security-context-py]] | **Line:** 469
**Signature:** `build_execution_context() → ExecutionContext`

**Class:** [[core-security-context-py-SecurityContext]]

Build an ExecutionContext pre-wired to the current env.

The context allows reads/writes under the env's workspace and
data_dir, and denies writes to the forbidden production paths
when running inside an isolated env.
