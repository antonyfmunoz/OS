---
type: codebase-file
path: eos_ai/higgsfield_client.py
module: eos_ai.higgsfield_client
lines: 120
size: 4259
generated: 2026-04-12
---

# eos_ai/higgsfield_client.py

Higgsfield Cloud API wrapper for EOS.

Thin layer over the first-party `higgsfield-client` Python SDK that:

- reads `HIGGSFIELD_API_KEY` + `HIGGSFIELD_API_KEY_SECRET` from /opt/OS/eos_ai/.env
...

**Lines:** 120 | **Size:** 4,259 bytes

## Depends On

- [[eos_ai-db-py]]

## Used By

- [[scripts-higgsfield_smoke_test-py]]

## Contains

- **fn** [[eos_ai-higgsfield_client-py-generate]]`(venture, model_id) → str`
- **fn** [[eos_ai-higgsfield_client-py-get_status]]`(request_id) → str`
- **fn** [[eos_ai-higgsfield_client-py-cancel]]`(request_id) → None`

## Import Statements

```python
from __future__ import annotations
import json
import os
import sys
from dotenv import load_dotenv
import higgsfield_client as hf
from eos_ai.db import get_conn
```
