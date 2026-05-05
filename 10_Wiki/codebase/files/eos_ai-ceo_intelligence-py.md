---
type: codebase-file
path: eos_ai/ceo_intelligence.py
module: eos_ai.ceo_intelligence
lines: 727
size: 20821
generated: 2026-04-12
---

# eos_ai/ceo_intelligence.py

CEO Intelligence — real-time business diagnostics.

Gives the CEO agent data-driven awareness of:
- Active constraint (Leads/Sales/Delivery/Profit)
- Offer stage position (I/II/III)
...

**Lines:** 727 | **Size:** 20,821 bytes

## Contains

- **fn** [[eos_ai-ceo_intelligence-py-_get_benchmarks]]`(venture_id) → dict`
- **fn** [[eos_ai-ceo_intelligence-py-get_funnel_metrics]]`(venture_id, ctx, days) → dict`
- **fn** [[eos_ai-ceo_intelligence-py-diagnose_constraint]]`(venture_id, ctx) → dict`
- **fn** [[eos_ai-ceo_intelligence-py-get_offer_stage]]`(venture_id, ctx) → dict`
- **fn** [[eos_ai-ceo_intelligence-py-get_agent_performance]]`(ctx, days) → dict`
- **fn** [[eos_ai-ceo_intelligence-py-generate_ceo_brief]]`(venture_id, venture_name, ctx) → str`

## Import Statements

```python
import json
import logging
import os
from datetime import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
```
