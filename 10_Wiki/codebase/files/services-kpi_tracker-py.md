---
type: codebase-file
path: services/kpi_tracker.py
module: services.kpi_tracker
lines: 412
size: 14937
tags: [entry-point]
generated: 2026-05-07
---

# services/kpi_tracker.py

> **ENTRY POINT** — Contains `if __name__` or server start.

*No docstring.*

**Lines:** 412 | **Size:** 14,937 bytes

## Contains

- **fn** [[services-kpi_tracker-py-get_pipeline_counts]]`()`
- **fn** [[services-kpi_tracker-py-get_scraper_stats]]`()`
- **fn** [[services-kpi_tracker-py-get_daily_log]]`()`
- **fn** [[services-kpi_tracker-py-get_conversation_stats]]`()`
- **fn** [[services-kpi_tracker-py-_parse_lead_frontmatter]]`(filepath)`
- **fn** [[services-kpi_tracker-py-get_opener_stats]]`()`
- **fn** [[services-kpi_tracker-py-get_hashtag_stats]]`()`
- **fn** [[services-kpi_tracker-py-append_kpi_history]]`(dms_sent, replied_count)`
- **fn** [[services-kpi_tracker-py-get_reply_rate_trend]]`(days)`
- **fn** [[services-kpi_tracker-py-get_hashtag_report]]`()`
- **fn** [[services-kpi_tracker-py-build_eod_report]]`(pipeline_counts, scraper_stats, conversation_stats, daily_log)`
- **fn** [[services-kpi_tracker-py-send_telegram]]`(text)`
- **fn** [[services-kpi_tracker-py-main]]`()`

## Import Statements

```python
import os
import sys
import json
import glob
import datetime
import requests
from dotenv import load_dotenv
import cost_tracker
```
