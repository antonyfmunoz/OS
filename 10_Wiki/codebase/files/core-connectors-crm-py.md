---
type: codebase-file
path: core/connectors/crm.py
module: core.connectors.crm
lines: 164
size: 5515
generated: 2026-05-07
---

# core/connectors/crm.py

CRM Connector — ingest lead and pipeline status changes.

Supports:
- Lead status transitions
- Pipeline stage tracking
...

**Lines:** 164 | **Size:** 5,515 bytes

## Depends On

- [[core-connectors-base-py]]

## Contains

- **class** [[core-connectors-crm-py-CrmConnector]] — 6 methods

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
```
