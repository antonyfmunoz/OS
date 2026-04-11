---
type: codebase-file
path: services/calendly_webhook.py
module: services.calendly_webhook
lines: 445
size: 16353
tags: [entry-point]
generated: 2026-04-11
---

# services/calendly_webhook.py

> **ENTRY POINT** — Contains `if __name__` or server start.

*No docstring.*

**Lines:** 445 | **Size:** 16,353 bytes

## Depends On

- [[eos_ai-memory-py]]

## Contains

- **fn** [[services-calendly_webhook-py-_log_calendly_outcome]]`(username, outcome_type, score, notes)`
- **fn** [[services-calendly_webhook-py-_detect_venture_from_event]]`(event_name) → str`
- **fn** [[services-calendly_webhook-py-verify_signature]]`(payload, signature)`
- **fn** [[services-calendly_webhook-py-send_telegram]]`(text)`
- **fn** [[services-calendly_webhook-py-find_lead_by_name_or_email]]`(name, email)`
- **fn** [[services-calendly_webhook-py-move_pipeline_card]]`(username, from_stage, to_stage)`
- **fn** [[services-calendly_webhook-py-update_lead_file]]`(filepath, new_stage, event_time, cancel_reason)`
- **fn** [[services-calendly_webhook-py-update_notion_lead_stage]]`(name, email, new_stage) → bool`
- **fn** [[services-calendly_webhook-py-calendly_webhook]]`()`
- **fn** [[services-calendly_webhook-py-health]]`()`

## Import Statements

```python
import os
import json
import hmac
import hashlib
import datetime
import glob
import re
import requests
from flask import Flask
from flask import request
from flask import jsonify
from dotenv import load_dotenv
import sys as _sys
from eos_ai.memory import AgentMemory
```
