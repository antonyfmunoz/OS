---
type: codebase-function
file: eos_ai/substrate/session_orchestration.py
line: 229
generated: 2026-05-07
---

# ensure_expected_sessions

**File:** [[eos_ai-substrate-session_orchestration-py]] | **Line:** 229
**Signature:** `ensure_expected_sessions() → dict[str, Any]`

Ensure all expected sessions exist. Idempotent.

Returns a dict with key ``ensured`` — a list of per-session result dicts
each containing ``session_name``, ``target``, ``action``, and ``detail``.

...

## Calls

- [[eos_ai-substrate-session_orchestration-py-_log]]
- [[eos_ai-substrate-session_orchestration-py-expected_sessions]]

## Called By

- [[scripts-substrate_session_orchestration_smoke_test-py-test_recovery]]
