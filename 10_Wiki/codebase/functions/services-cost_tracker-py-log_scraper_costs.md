---
type: codebase-function
file: services/cost_tracker.py
line: 277
generated: 2026-04-12
---

# log_scraper_costs

**File:** [[services-cost_tracker-py]] | **Line:** 277
**Signature:** `log_scraper_costs(apify_results, haiku_calls, haiku_input_tokens, haiku_output_tokens)`

Calculate scraper costs, update log, save, and return total cost for this run.

## Calls

- [[services-cost_tracker-py-_deep_copy_empty_day]]
- [[services-cost_tracker-py-_month_key]]
- [[services-cost_tracker-py-_today_key]]
- [[services-cost_tracker-py-load_log]]
- [[services-cost_tracker-py-save_log]]
