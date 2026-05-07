---
type: codebase-function
file: eos_ai/substrate/session_orchestration.py
line: 65
generated: 2026-05-07
---

# expected_sessions

**File:** [[eos_ai-substrate-session_orchestration-py]] | **Line:** 65
**Signature:** `expected_sessions() → list[ExpectedSession]`

Return the expected session topology.

Includes the two default sessions plus any additional entries from the
``EOS_EXTRA_EXPECTED_SESSIONS`` environment variable.

...

## Calls

- [[eos_ai-substrate-session_orchestration-py-_log]]

## Called By

- [[eos_ai-substrate-session_orchestration-py-ensure_expected_sessions]]
- [[eos_ai-substrate-session_orchestration-py-reconcile_sessions]]
- [[eos_ai-substrate-session_orchestration-py-session_readiness_report]]
- [[scripts-substrate_session_orchestration_smoke_test-py-test_registry]]
