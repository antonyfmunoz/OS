---
type: codebase-file
path: eos_ai/stakeholder_map.py
module: eos_ai.stakeholder_map
lines: 251
size: 7900
generated: 2026-04-12
---

# eos_ai/stakeholder_map.py

Stakeholder Map — tracks key stakeholders per venture,
their status, influence, and what they need.

**Lines:** 251 | **Size:** 7,900 bytes

## Contains

- **fn** [[eos_ai-stakeholder_map-py-add_stakeholder]]`(name, venture, role, influence, status, notes, email, ctx) → bool`
- **fn** [[eos_ai-stakeholder_map-py-get_stakeholders]]`(venture, ctx) → list[dict]`
- **fn** [[eos_ai-stakeholder_map-py-generate_stakeholder_brief]]`(venture, ctx) → str`
- **fn** [[eos_ai-stakeholder_map-py-add_board_member]]`(name, email, venture_id, role, notes, ctx) → bool`
- **fn** [[eos_ai-stakeholder_map-py-get_board_members]]`(venture_id, ctx) → list`
- **fn** [[eos_ai-stakeholder_map-py-generate_board_update_brief]]`(venture_id, ctx) → str`

## Import Statements

```python
import os
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
```
