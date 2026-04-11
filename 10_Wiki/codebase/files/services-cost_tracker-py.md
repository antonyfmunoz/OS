---
type: codebase-file
path: services/cost_tracker.py
module: services.cost_tracker
lines: 415
size: 13097
generated: 2026-04-11
---

# services/cost_tracker.py

*No docstring.*

**Lines:** 415 | **Size:** 13,097 bytes

## Contains

- **fn** [[services-cost_tracker-py-_deep_copy_empty_day]]`()`
- **fn** [[services-cost_tracker-py-load_log]]`()`
- **fn** [[services-cost_tracker-py-save_log]]`(log)`
- **fn** [[services-cost_tracker-py-_today_key]]`()`
- **fn** [[services-cost_tracker-py-_month_key]]`()`
- **fn** [[services-cost_tracker-py-sync_apify_balance]]`()`
- **fn** [[services-cost_tracker-py-sync_and_update_apify_log]]`()`
- **fn** [[services-cost_tracker-py-log_apify_runs]]`(hashtag_runs, comment_runs, profile_runs)`
- **fn** [[services-cost_tracker-py-log_scraper_costs]]`(apify_results, haiku_calls, haiku_input_tokens, haiku_output_tokens)`
- **fn** [[services-cost_tracker-py-log_copilot_costs]]`(sonnet_calls, sonnet_input_tokens, sonnet_output_tokens)`
- **fn** [[services-cost_tracker-py-get_today_costs]]`()`
- **fn** [[services-cost_tracker-py-get_monthly_costs]]`(month_str)`
- **fn** [[services-cost_tracker-py-get_all_time_total]]`()`
- **fn** [[services-cost_tracker-py-get_cost_summary]]`()`
- **fn** [[services-cost_tracker-py-format_cost_report]]`()`

## Import Statements

```python
import os
import json
import datetime
from dotenv import load_dotenv
```
