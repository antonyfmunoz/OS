---
type: codebase-function
file: eos_ai/substrate/result_query.py
line: 146
generated: 2026-04-11
---

# unresolved_rituals

**File:** [[eos_ai-substrate-result_query-py]] | **Line:** 146
**Signature:** `unresolved_rituals(limit) → list[dict]`

Recent rituals whose body_actions include at least one action_id that
has no matching result yet. Bounded, read-only, never raises.

## Calls

- [[eos_ai-substrate-result_store-py-ResultStore-get]]
- [[eos_ai-substrate-result_store-py-get_result_store]]

## Called By

- [[scripts-substrate_drain_station-py-main]]
- [[scripts-substrate_durable_result_smoke_test-py-main]]
