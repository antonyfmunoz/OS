---
type: codebase-function
file: eos_ai/substrate/session_orchestration.py
line: 139
generated: 2026-04-12
---

# session_health

**File:** [[eos_ai-substrate-session_orchestration-py]] | **Line:** 139
**Signature:** `session_health(target, session_name) → dict[str, Any]`

Check health of a single session.

Returns a dict with keys: ``session_name``, ``target``, ``health``,
``status``, ``checked_at``, ``detail``. Never raises.

## Calls

- [[eos_ai-substrate-session_orchestration-py-_now_iso]]

## Called By

- [[eos_ai-substrate-session_orchestration-py-session_readiness_report]]
- [[scripts-substrate_session_orchestration_smoke_test-py-test_health]]
