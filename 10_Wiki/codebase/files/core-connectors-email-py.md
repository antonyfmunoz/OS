---
type: codebase-file
path: core/connectors/email.py
module: core.connectors.email
lines: 160
size: 5569
generated: 2026-05-07
---

# core/connectors/email.py

Email / DM Connector — ingest outreach reply metrics.

Supports:
- Live API integration (when available)
- JSON/CSV file fallback for MVP
...

**Lines:** 160 | **Size:** 5,569 bytes

## Depends On

- [[core-connectors-base-py]]

## Contains

- **class** [[core-connectors-email-py-EmailConnector]] — 6 methods

## Import Statements

```python
from __future__ import annotations
import time
from pathlib import Path
from typing import Any
from core.connectors.base import Connector
from core.connectors.base import CsvFileAdapter
from core.connectors.base import JsonFileAdapter
from core.connectors.base import RealSignal
from core.connectors.base import WebhookPayloadAdapter
from core.connectors.base import dict_to_signal
```
