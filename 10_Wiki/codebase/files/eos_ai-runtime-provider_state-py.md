---
type: codebase-file
path: eos_ai/runtime/provider_state.py
module: eos_ai.runtime.provider_state
lines: 288
size: 10365
generated: 2026-05-07
---

# eos_ai/runtime/provider_state.py

Global Provider State + Backpressure + Execution Budget.

Single module that prevents system-wide failure cascades under provider
outages or resource exhaustion.  Process-wide singleton — shared across
all threads (ambient loop, gateway, SessionWatcher, etc.).
...

**Lines:** 288 | **Size:** 10,365 bytes

## Contains

- **class** [[eos_ai-runtime-provider_state-py-ProviderStatus]] — 0 methods
- **class** [[eos_ai-runtime-provider_state-py-SystemStatus]] — 0 methods
- **class** [[eos_ai-runtime-provider_state-py-ProviderState]] — 3 methods
- **class** [[eos_ai-runtime-provider_state-py-ExecutionBudget]] — 6 methods
- **class** [[eos_ai-runtime-provider_state-py-SystemProviderState]] — 10 methods
- **fn** [[eos_ai-runtime-provider_state-py-get_system_state]]`() → SystemProviderState`

## Import Statements

```python
from __future__ import annotations
import os
import time
import logging
import threading
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
```
