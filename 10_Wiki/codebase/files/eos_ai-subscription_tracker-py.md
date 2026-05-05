---
type: codebase-file
path: eos_ai/subscription_tracker.py
module: eos_ai.subscription_tracker
lines: 126
size: 4009
generated: 2026-04-12
---

# eos_ai/subscription_tracker.py

Subscription Tracker — maintains a registry of active
subscriptions, renewal dates, and costs.

**Lines:** 126 | **Size:** 4,009 bytes

## Contains

- **fn** [[eos_ai-subscription_tracker-py-get_subscriptions]]`(ctx) → list[dict]`
- **fn** [[eos_ai-subscription_tracker-py-add_subscription]]`(vendor, amount, billing_cycle, next_renewal, category, notes, ctx) → bool`
- **fn** [[eos_ai-subscription_tracker-py-get_upcoming_renewals]]`(days, ctx) → list[dict]`
- **fn** [[eos_ai-subscription_tracker-py-get_monthly_subscription_total]]`(ctx) → float`

## Import Statements

```python
import json
import logging
from datetime import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo
```
