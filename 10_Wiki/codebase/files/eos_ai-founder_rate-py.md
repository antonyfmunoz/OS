---
type: codebase-file
path: eos_ai/founder_rate.py
module: eos_ai.founder_rate
lines: 299
size: 9832
generated: 2026-04-12
---

# eos_ai/founder_rate.py

Founder Rate — Dan Martell's framework for valuing
founder time and making delegation decisions.
Leverage Loop = Annual income / 2000 hours / 4

**Lines:** 299 | **Size:** 9,832 bytes

## Contains

- **fn** [[eos_ai-founder_rate-py-calculate_founder_rate]]`(annual_income, working_hours_per_year) → dict`
- **fn** [[eos_ai-founder_rate-py-store_founder_rate]]`(annual_income, ctx) → bool`
- **fn** [[eos_ai-founder_rate-py-get_current_founder_rate]]`(ctx) → dict`
- **fn** [[eos_ai-founder_rate-py-log_time_block]]`(activity, duration_minutes, energy, estimated_value, ctx) → bool`
- **fn** [[eos_ai-founder_rate-py-get_time_audit_summary]]`(days, ctx) → dict`
- **fn** [[eos_ai-founder_rate-py-add_to_no_list]]`(item, reason, ctx) → bool`
- **fn** [[eos_ai-founder_rate-py-get_no_list]]`(ctx) → list[dict]`
- **fn** [[eos_ai-founder_rate-py-check_against_no_list]]`(text, ctx) → list[str]`
- **fn** [[eos_ai-founder_rate-py-detect_delegation_threshold]]`(ctx) → list[dict]`

## Import Statements

```python
import json
import logging
from datetime import datetime
from pathlib import Path as _Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
```
