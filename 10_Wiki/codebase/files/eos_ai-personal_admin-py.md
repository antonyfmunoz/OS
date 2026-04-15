---
type: codebase-file
path: eos_ai/personal_admin.py
module: eos_ai.personal_admin
lines: 142
size: 4675
generated: 2026-04-12
---

# eos_ai/personal_admin.py

Personal Admin — important dates, gift research,
and personal appointment management.

**Lines:** 142 | **Size:** 4,675 bytes

## Contains

- **fn** [[eos_ai-personal_admin-py-add_important_date]]`(person, date, date_type, notes, ctx) → bool`
- **fn** [[eos_ai-personal_admin-py-get_upcoming_dates]]`(days, ctx) → list[dict]`
- **fn** [[eos_ai-personal_admin-py-research_gift]]`(person, occasion, budget, context) → str`

## Import Statements

```python
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
```
