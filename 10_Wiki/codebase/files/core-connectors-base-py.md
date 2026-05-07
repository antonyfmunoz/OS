---
type: codebase-file
path: core/connectors/base.py
module: core.connectors.base
lines: 232
size: 7485
generated: 2026-05-07
---

# core/connectors/base.py

Connector Base — common interface for real data ingestion.

Every connector implements the same protocol:
    healthcheck()   → is the source reachable?
    fetch_signals() → pull raw data and normalize
...

**Lines:** 232 | **Size:** 7,485 bytes

## Used By

- [[core-connectors-content-py]]
- [[core-connectors-crm-py]]
- [[core-connectors-email-py]]

## Contains

- **class** [[core-connectors-base-py-RealSignal]] — 2 methods
- **class** [[core-connectors-base-py-Connector]] — 6 methods
- **class** [[core-connectors-base-py-JsonFileAdapter]] — 1 methods
- **class** [[core-connectors-base-py-CsvFileAdapter]] — 1 methods
- **class** [[core-connectors-base-py-LogFileAdapter]] — 1 methods
- **class** [[core-connectors-base-py-WebhookPayloadAdapter]] — 1 methods
- **fn** [[core-connectors-base-py-dict_to_signal]]`(raw, source) → RealSignal`
- **fn** [[core-connectors-base-py-aggregate_signals]]`(signals) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import csv
import io
import json
import time
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any
```
