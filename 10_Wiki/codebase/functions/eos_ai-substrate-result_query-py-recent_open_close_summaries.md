---
type: codebase-function
file: eos_ai/substrate/result_query.py
line: 263
generated: 2026-05-07
---

# recent_open_close_summaries

**File:** [[eos_ai-substrate-result_query-py]] | **Line:** 263
**Signature:** `recent_open_close_summaries(limit) → list[dict]`

Filter the most recent rituals to open_day / close_day only and surface
the operator-relevant outputs (readiness snapshot + close_day_summary +
body_action_count). JSON-friendly, bounded.

## Calls

- [[eos_ai-substrate-result_store-py-ResultStore-get]]

## Called By

- [[scripts-substrate_drain_station-py-main]]
