---
type: codebase-file
path: eos_ai/substrate/browser_agent.py
module: eos_ai.substrate.browser_agent
lines: 528
size: 18865
generated: 2026-05-07
---

# eos_ai/substrate/browser_agent.py

Browser agent — real Playwright execution surface for the substrate.

Generic browser automation layer using headless Chromium via Playwright.
NOT EOS-specific. Does not import anything from eos_ai.platforms.

...

**Lines:** 528 | **Size:** 18,865 bytes

## Contains

- **class** [[eos_ai-substrate-browser_agent-py-BrowserActionType]] — 0 methods
- **class** [[eos_ai-substrate-browser_agent-py-BrowserActionResult]] — 1 methods
- **class** [[eos_ai-substrate-browser_agent-py-BrowserAgent]] — 17 methods
- **fn** [[eos_ai-substrate-browser_agent-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-browser_agent-py-_utcnow]]`() → str`
- **fn** [[eos_ai-substrate-browser_agent-py-_stream_browser_event]]`(event_type_name, action, payload) → None`
- **fn** [[eos_ai-substrate-browser_agent-py-_stream_browser_result]]`(action, result) → None`
- **fn** [[eos_ai-substrate-browser_agent-py-get_browser_agent]]`(headless) → BrowserAgent`
- **fn** [[eos_ai-substrate-browser_agent-py-execute_browser_action]]`(action, payload, headless) → BrowserActionResult`

## Import Statements

```python
from __future__ import annotations
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
from typing import Optional
```
