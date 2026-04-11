---
type: codebase-file
path: eos_ai/browser_agent.py
module: eos_ai.browser_agent
lines: 558
size: 20908
tags: [entry-point]
generated: 2026-04-11
---

# eos_ai/browser_agent.py

> **ENTRY POINT** — Contains `if __name__` or server start.

BrowserAgent — Playwright-based web operator for EOS agents.

Gives agents the ability to operate any website or web application.
Same pattern as gws_connector.py — a clean wrapper that agents call,
it executes in the browser, returns results.
...

**Lines:** 558 | **Size:** 20,908 bytes

## Contains

- **class** [[eos_ai-browser_agent-py-BrowserAgent]] — 16 methods
- **class** [[eos_ai-browser_agent-py-ManusAgent]] — 1 methods
- **class** [[eos_ai-browser_agent-py-InstagramAgent]] — 2 methods
- **fn** [[eos_ai-browser_agent-py-_synthesize_findings]]`(task, page_states, action_log) → str`
- **fn** [[eos_ai-browser_agent-py-run_browser_task]]`(url, task, ctx) → dict`

## Import Statements

```python
import json
import re
from pathlib import Path
from dotenv import load_dotenv
```
