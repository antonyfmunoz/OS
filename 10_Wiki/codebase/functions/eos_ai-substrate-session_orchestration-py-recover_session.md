---
type: codebase-function
file: eos_ai/substrate/session_orchestration.py
line: 287
generated: 2026-04-12
---

# recover_session

**File:** [[eos_ai-substrate-session_orchestration-py]] | **Line:** 287
**Signature:** `recover_session(target, session_name) → dict[str, Any]`

Recover a specific session.

Strategies:
  - ``"recreate"``: kill and recreate via ``session_control.reset_session``
  - ``"ensure"``: just ensure exists via ``ensure_session``
...

## Called By

- [[scripts-substrate_session_orchestration_smoke_test-py-test_recovery]]
