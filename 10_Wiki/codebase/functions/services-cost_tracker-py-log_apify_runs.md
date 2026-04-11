---
type: codebase-function
file: services/cost_tracker.py
line: 185
generated: 2026-04-11
---

# log_apify_runs

**File:** [[services-cost_tracker-py]] | **Line:** 185
**Signature:** `log_apify_runs(hashtag_runs, comment_runs, profile_runs)`

Track actual Apify actor runs with free tier calculation.
Syncs from Apify API every call for real billing data.

## Calls

- [[services-cost_tracker-py-_deep_copy_empty_day]]
- [[services-cost_tracker-py-_month_key]]
- [[services-cost_tracker-py-_today_key]]
- [[services-cost_tracker-py-load_log]]
- [[services-cost_tracker-py-save_log]]
- [[services-cost_tracker-py-sync_apify_balance]]
