---
type: codebase-file
path: core/connectors/content.py
module: core.connectors.content
lines: 157
size: 5372
generated: 2026-05-07
---

# core/connectors/content.py

Content Connector — ingest content performance metrics.

Supports:
- Social media metrics (views, likes, comments, saves, shares)
- Audience growth (follower_delta)
...

**Lines:** 157 | **Size:** 5,372 bytes

## Depends On

- [[core-connectors-base-py]]

## Contains

- **class** [[core-connectors-content-py-ContentConnector]] — 6 methods

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
