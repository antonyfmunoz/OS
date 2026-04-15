---
type: codebase-file
path: eos_ai/gateway.py
module: eos_ai.gateway
lines: 1882
size: 72321
tags: [critical]
generated: 2026-04-12
---

# eos_ai/gateway.py

> **CRITICAL FILE** — Core infrastructure. Read before modifying.

EOSGateway — single control plane for all AI operations.

Every AI request enters here. Nothing calls agent_runtime, event_bus,
orchestrator, or agent_teams directly from outside eos_ai.

...

**Lines:** 1882 | **Size:** 72,321 bytes

## Depends On

- [[eos_ai-db-py]]

## Used By

- [[services-discord_bot-py]]

## Contains

- **class** [[eos_ai-gateway-py-EOSGateway]] — 27 methods
- **fn** [[eos_ai-gateway-py-_utcnow]]`() → str`
- **fn** [[eos_ai-gateway-py-_timestamp_id]]`() → str`
- **fn** [[eos_ai-gateway-py-get_gateway]]`() → EOSGateway`
- **fn** [[eos_ai-gateway-py-ingest_external_context]]`(source, content, context_type, venture_id) → str`

## Import Statements

```python
import json
import os
import re as _re
import sys
import threading
import uuid as _uuid_mod
from datetime import datetime
from datetime import timezone
from pathlib import Path
from eos_ai.db import get_conn
from eos_ai.db import ORG_ID
```
