---
type: codebase-function
file: eos_ai/substrate/session_orchestration.py
line: 182
generated: 2026-05-07
---

# session_readiness_report

**File:** [[eos_ai-substrate-session_orchestration-py]] | **Line:** 182
**Signature:** `session_readiness_report() → dict[str, Any]`

Full health report across all expected sessions.

Returns a dict with keys: ``checked_at``, ``expected_count``,
``healthy_count``, ``degraded_count``, ``missing_count``, ``sessions``,
``overall``.
...

## Calls

- [[eos_ai-substrate-session_orchestration-py-_now_iso]]
- [[eos_ai-substrate-session_orchestration-py-expected_sessions]]
- [[eos_ai-substrate-session_orchestration-py-session_health]]

## Called By

- [[scripts-substrate_session_orchestration_smoke_test-py-test_health]]
