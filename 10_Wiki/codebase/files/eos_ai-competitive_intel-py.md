---
type: codebase-file
path: eos_ai/competitive_intel.py
module: eos_ai.competitive_intel
lines: 149
size: 4891
generated: 2026-04-11
---

# eos_ai/competitive_intel.py

Competitive Intelligence — tracks competitor signals
and synthesizes implications for each venture.

**Lines:** 149 | **Size:** 4,891 bytes

## Contains

- **fn** [[eos_ai-competitive_intel-py-log_competitor_signal]]`(venture, competitor, signal, implication, ctx) → bool`
- **fn** [[eos_ai-competitive_intel-py-get_recent_signals]]`(venture, days, ctx) → list[dict]`
- **fn** [[eos_ai-competitive_intel-py-synthesize_competitive_landscape]]`(venture, ctx) → str`

## Import Statements

```python
import os
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
```
