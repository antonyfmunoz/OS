---
type: codebase-function
file: scripts/orchestrator.py
line: 204
generated: 2026-04-12
---

# Verifier.system_is_healthy

**File:** [[scripts-orchestrator-py]] | **Line:** 204
**Signature:** `system_is_healthy() → tuple[bool, str]`

**Class:** [[scripts-orchestrator-py-Verifier]]

Cheap liveness check before submitting work.

Intentionally permissive — we log the signal but don't block. The
orchestrator is meant to run on a contended VPS; a strict load guard
here would wedge the system into permanent BACKOFF. We only hard-fail
...

## Called By

- [[scripts-orchestrator-py-Orchestrator-submit]]

## Decorators

- `@staticmethod`
