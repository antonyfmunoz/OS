---
type: codebase-function
file: services/cost_tracker.py
line: 75
generated: 2026-04-12
---

# load_log

**File:** [[services-cost_tracker-py]] | **Line:** 75
**Signature:** `load_log()`

Read COST_LOG_FILE, return dict. Returns empty structure if file doesn't exist.

## Called By

- [[services-cost_tracker-py-format_cost_report]]
- [[services-cost_tracker-py-get_all_time_total]]
- [[services-cost_tracker-py-get_monthly_costs]]
- [[services-cost_tracker-py-get_today_costs]]
- [[services-cost_tracker-py-log_apify_runs]]
- [[services-cost_tracker-py-log_copilot_costs]]
- [[services-cost_tracker-py-log_scraper_costs]]
- [[services-cost_tracker-py-sync_and_update_apify_log]]
