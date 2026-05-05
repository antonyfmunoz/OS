---
type: codebase-file
path: eos_ai/provider_health.py
module: eos_ai.provider_health
lines: 225
size: 7719
tags: [entry-point]
generated: 2026-04-12
---

# eos_ai/provider_health.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Provider Health — single source of truth for "can we run an LLM job right now?"

Used by:
- scheduled cron wrappers, to skip LLM-dependent work when no provider is healthy
- operator status script, to show inspectable health
...

**Lines:** 225 | **Size:** 7,719 bytes

## Used By

- [[scripts-eos_status-py]]

## Contains

- **class** [[eos_ai-provider_health-py-ProviderHealth]] — 4 methods
- **fn** [[eos_ai-provider_health-py-_has_env]]`(name) → bool`
- **fn** [[eos_ai-provider_health-py-check_anthropic]]`() → tuple[bool, str]`
- **fn** [[eos_ai-provider_health-py-check_gemini]]`() → tuple[bool, str]`
- **fn** [[eos_ai-provider_health-py-check_perplexity]]`() → tuple[bool, str]`
- **fn** [[eos_ai-provider_health-py-check_groq]]`() → tuple[bool, str]`
- **fn** [[eos_ai-provider_health-py-check_ollama]]`() → tuple[bool, str]`
- **fn** [[eos_ai-provider_health-py-check_cc_sdk]]`() → tuple[bool, str]`
- **fn** [[eos_ai-provider_health-py-check_all]]`() → ProviderHealth`
- **fn** [[eos_ai-provider_health-py-require_llm_or_skip]]`(job_name, log_path) → ProviderHealth`

## Import Statements

```python
from __future__ import annotations
import os
import time
from dataclasses import dataclass
from dataclasses import field
from dataclasses import asdict
from pathlib import Path
from typing import Optional
```
