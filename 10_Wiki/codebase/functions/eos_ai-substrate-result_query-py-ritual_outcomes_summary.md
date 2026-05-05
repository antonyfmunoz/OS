---
type: codebase-function
file: eos_ai/substrate/result_query.py
line: 422
generated: 2026-04-12
---

# ritual_outcomes_summary

**File:** [[eos_ai-substrate-result_query-py]] | **Line:** 422
**Signature:** `ritual_outcomes_summary(limit) → list[dict]`

Walk the most recent rituals and emit a bounded summary of their
station-action outcomes. Reads `ritual.outputs["result_summary"]` which
is populated by `ritual_reconciler.reconcile_ritual`.

Useful after a drain+reconcile pass to answer "how did the last few
...

## Calls

- [[eos_ai-substrate-result_store-py-ResultStore-get]]

## Called By

- [[scripts-substrate_drain_station-py-main]]
- [[scripts-substrate_durable_result_smoke_test-py-main]]
