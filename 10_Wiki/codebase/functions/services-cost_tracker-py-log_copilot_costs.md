---
type: codebase-function
file: services/cost_tracker.py
line: 315
generated: 2026-04-12
---

# log_copilot_costs

**File:** [[services-cost_tracker-py]] | **Line:** 315
**Signature:** `log_copilot_costs(sonnet_calls, sonnet_input_tokens, sonnet_output_tokens)`

Calculate copilot costs, update log, save, and return total cost for this call.

## Calls

- [[services-cost_tracker-py-_deep_copy_empty_day]]
- [[services-cost_tracker-py-_month_key]]
- [[services-cost_tracker-py-_today_key]]
- [[services-cost_tracker-py-load_log]]
- [[services-cost_tracker-py-save_log]]
