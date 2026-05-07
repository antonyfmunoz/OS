---
type: codebase-file
path: services/overnight_scrape.py
module: services.overnight_scrape
lines: 252
size: 8100
tags: [entry-point]
generated: 2026-05-07
---

# services/overnight_scrape.py

> **ENTRY POINT** — Contains `if __name__` or server start.

*No docstring.*

**Lines:** 252 | **Size:** 8,100 bytes

## Contains

- **fn** [[services-overnight_scrape-py-send_telegram]]`(text)`
- **fn** [[services-overnight_scrape-py-count_new_leads_today]]`()`
- **fn** [[services-overnight_scrape-py-get_today_cost]]`()`
- **fn** [[services-overnight_scrape-py-force_group_a]]`()`
- **fn** [[services-overnight_scrape-py-get_scrape_stats]]`()`
- **fn** [[services-overnight_scrape-py-get_hashtag_learning]]`()`
- **fn** [[services-overnight_scrape-py-check_cost_approval]]`(current_cost, leads_so_far, approved_limit)`
- **fn** [[services-overnight_scrape-py-run_scraper]]`(ignore_cache)`
- **fn** [[services-overnight_scrape-py-run_scorer]]`()`
- **fn** [[services-overnight_scrape-py-main]]`()`

## Import Statements

```python
import subprocess
import sys
import json
import glob
import time
import datetime
import requests
import os
from dotenv import load_dotenv
```
