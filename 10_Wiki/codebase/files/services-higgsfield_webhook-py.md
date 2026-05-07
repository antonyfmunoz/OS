---
type: codebase-file
path: services/higgsfield_webhook.py
module: services.higgsfield_webhook
lines: 141
size: 4765
tags: [entry-point]
generated: 2026-05-07
---

# services/higgsfield_webhook.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Higgsfield Cloud API webhook receiver.

Flask endpoint at POST /webhooks/higgsfield that:

1. Validates the incoming request_id exists in higgsfield_jobs and is
...

**Lines:** 141 | **Size:** 4,765 bytes

## Depends On

- [[eos_ai-db-py]]

## Contains

- **fn** [[services-higgsfield_webhook-py-_download]]`(url, dest) → None`
- **fn** [[services-higgsfield_webhook-py-_extract_output_url]]`(payload) → tuple[str | None, str]`
- **fn** [[services-higgsfield_webhook-py-handle_webhook]]`(payload) → tuple[dict, int]`
- **fn** [[services-higgsfield_webhook-py-register]]`(app) → None`

## Import Statements

```python
from __future__ import annotations
import os
import sys
from datetime import datetime
from pathlib import Path
import requests
from flask import Flask
from flask import jsonify
from flask import request
from eos_ai.db import get_conn
```
