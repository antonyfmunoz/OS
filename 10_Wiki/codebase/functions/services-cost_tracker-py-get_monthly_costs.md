---
type: codebase-function
file: services/cost_tracker.py
line: 356
generated: 2026-04-12
---

# get_monthly_costs

**File:** [[services-cost_tracker-py]] | **Line:** 356
**Signature:** `get_monthly_costs(month_str)`

Return monthly total. month_str format: '2026-03'. Defaults to current month.

## Calls

- [[services-cost_tracker-py-_month_key]]
- [[services-cost_tracker-py-load_log]]

## Called By

- [[services-cost_tracker-py-format_cost_report]]
- [[services-cost_tracker-py-get_cost_summary]]
