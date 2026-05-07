---
type: codebase-function
file: eos_ai/substrate/session_orchestration.py
line: 347
generated: 2026-05-07
---

# reconcile_sessions

**File:** [[eos_ai-substrate-session_orchestration-py]] | **Line:** 347
**Signature:** `reconcile_sessions() → dict[str, Any]`

Compare expected vs actual and return a reconciliation report.

Returns a dict with keys: ``expected``, ``actual``, ``matched``,
``unexpected``, ``missing``, ``recommendations``.

## Calls

- [[eos_ai-substrate-session_orchestration-py-actual_sessions]]
- [[eos_ai-substrate-session_orchestration-py-expected_sessions]]

## Called By

- [[scripts-substrate_session_orchestration_smoke_test-py-test_reconciliation]]
