---
type: codebase-file
path: eos_ai/cc_sdk.py
module: eos_ai.cc_sdk
lines: 322
size: 10633
generated: 2026-04-11
---

# eos_ai/cc_sdk.py

cc_sdk — Claude Code Agent SDK wrapper for EOS.

New provider for model_router. Uses claude-agent-sdk to run queries
through Claude Code's subprocess transport (local CLI).

...

**Lines:** 322 | **Size:** 10,633 bytes

## Used By

- [[eos_ai-model_router-py]]

## Contains

- **class** [[eos_ai-cc_sdk-py-CCResult]] — 0 methods
- **fn** [[eos_ai-cc_sdk-py-_is_nested_cc_session]]`() → bool`
- **fn** [[eos_ai-cc_sdk-py-query_cc]]`(prompt, system, task_type, session_id, max_budget_usd, agent_id, timeout) → CCResult | None`
- **fn** [[eos_ai-cc_sdk-py-_kill_orphaned_claude_procs]]`(before_pids) → None`
- **fn** [[eos_ai-cc_sdk-py-_get_claude_pids]]`() → set[int]`
- **fn** [[eos_ai-cc_sdk-py-query_cc_sync]]`(prompt, system, task_type, session_id, max_budget_usd, agent_id, timeout) → CCResult | None`

## Import Statements

```python
import asyncio
import logging
import os
import signal
import subprocess
import time
from dataclasses import dataclass
```
