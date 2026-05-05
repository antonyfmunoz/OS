---
type: codebase-class
file: core/security/execution.py
line: 217
generated: 2026-04-12
---

# RestrictedExecutor

**File:** [[core-security-execution-py]] | **Line:** 217

Runs commands under an ExecutionContext.

The executor is intentionally thin — it's just `subprocess.run` with
the context's guards applied before and after. No process namespace
magic. That belongs in a container layer.

## Methods

- [[core-security-execution-py-RestrictedExecutor-__init__]]`(ctx) → None` — 
- [[core-security-execution-py-RestrictedExecutor-run]]`(command) → ExecutionResult` — 
