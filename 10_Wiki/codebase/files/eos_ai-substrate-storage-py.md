---
type: codebase-file
path: eos_ai/substrate/storage.py
module: eos_ai.substrate.storage
lines: 212
size: 7664
generated: 2026-05-07
---

# eos_ai/substrate/storage.py

Substrate storage — minimal persistence for NodeRegistry and RitualRegistry.

Design rules:
  - Keep the schema TINY. One key/value surface, JSON blobs as values.
  - Safe default: JSON file at /opt/OS/eos_ai/.substrate_state.json.
...

**Lines:** 212 | **Size:** 7,664 bytes

## Used By

- [[eos_ai-substrate-control_bridge-py]]
- [[eos_ai-substrate-local_listener-py]]
- [[eos_ai-substrate-wake_producer-py]]

## Contains

- **class** [[eos_ai-substrate-storage-py-SubstrateStorage]] — 3 methods
- **class** [[eos_ai-substrate-storage-py-JSONFileStorage]] — 6 methods
- **class** [[eos_ai-substrate-storage-py-NeonStorage]] — 5 methods
- **fn** [[eos_ai-substrate-storage-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-storage-py-get_storage]]`(prefer) → SubstrateStorage`
- **fn** [[eos_ai-substrate-storage-py-reset_storage_for_tests]]`() → None`

## Import Statements

```python
from __future__ import annotations
import json
import os
import sys
import threading
from pathlib import Path
from typing import Any
from typing import Optional
from typing import Protocol
```
