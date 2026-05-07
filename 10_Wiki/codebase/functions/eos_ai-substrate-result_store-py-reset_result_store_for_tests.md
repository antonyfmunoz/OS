---
type: codebase-function
file: eos_ai/substrate/result_store.py
line: 241
generated: 2026-05-07
---

# reset_result_store_for_tests

**File:** [[eos_ai-substrate-result_store-py]] | **Line:** 241
**Signature:** `reset_result_store_for_tests() → None`

Drop the singleton. Next `get_result_store()` rehydrates from storage.

## Called By

- [[scripts-substrate_durable_result_smoke_test-py-main]]
- [[scripts-substrate_result_loop_smoke_test-py-main]]
- [[scripts-substrate_voice_eos_responder_smoke_test-py-main]]
- [[scripts-substrate_voice_session_smoke_test-py-main]]
