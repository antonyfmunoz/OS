---
type: codebase-function
file: services/cost_tracker.py
line: 349
generated: 2026-04-11
---

# get_today_costs

**File:** [[services-cost_tracker-py]] | **Line:** 349
**Signature:** `get_today_costs()`

Return today's full cost entry. Returns zeroed structure if no entry.

## Calls

- [[services-cost_tracker-py-_deep_copy_empty_day]]
- [[services-cost_tracker-py-_today_key]]
- [[services-cost_tracker-py-load_log]]

## Called By

- [[services-cost_tracker-py-format_cost_report]]
- [[services-cost_tracker-py-get_cost_summary]]
