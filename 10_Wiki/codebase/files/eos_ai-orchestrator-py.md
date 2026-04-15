---
type: codebase-file
path: eos_ai/orchestrator.py
module: eos_ai.orchestrator
lines: 1878
size: 72999
tags: [critical, entry-point]
generated: 2026-04-12
---

# eos_ai/orchestrator.py

> **CRITICAL FILE** — Core infrastructure. Read before modifying.

> **ENTRY POINT** — Contains `if __name__` or server start.

EOSOrchestrator — strategic intelligence layer.

Reads venture KPIs, queries 7-day memory stats, identifies the binding
constraint, and dispatches the morning brief via Telegram.

...

**Lines:** 1878 | **Size:** 72,999 bytes

## Depends On

- [[eos_ai-agent_runtime-py]]
- [[eos_ai-context-py]]
- [[eos_ai-db-py]]
- [[eos_ai-memory-py]]
- [[eos_ai-venture_knowledge-py]]

## Contains

- **class** [[eos_ai-orchestrator-py-CEOAgent]] — 4 methods
- **class** [[eos_ai-orchestrator-py-EOSOrchestrator]] — 6 methods
- **fn** [[eos_ai-orchestrator-py-_notify]]`(text) → None`
- **fn** [[eos_ai-orchestrator-py-_send_discord_webhook]]`(env_var, content, title, username) → None`
- **fn** [[eos_ai-orchestrator-py-_fmt_company_reports]]`(reports) → str`
- **fn** [[eos_ai-orchestrator-py-_fmt_signals]]`(signals) → str`
- **fn** [[eos_ai-orchestrator-py-_fmt_pending]]`(pending) → str`
- **fn** [[eos_ai-orchestrator-py-_fmt_patterns]]`(patterns) → str`
- **fn** [[eos_ai-orchestrator-py-run_full_morning_cycle]]`(ctx, return_content)`
- **fn** [[eos_ai-orchestrator-py-run_ceo_morning_delegation]]`(ctx, ventures) → None`
- **fn** [[eos_ai-orchestrator-py-check_proactive_triggers]]`(ctx) → list[str]`
- **fn** [[eos_ai-orchestrator-py-check_outcome_milestone]]`(ctx, new_outcome_count) → None`
- **fn** [[eos_ai-orchestrator-py-generate_morning_brief]]`(ctx) → str`
- **fn** [[eos_ai-orchestrator-py-write_to_notion_dashboard]]`(ctx, morning_data) → None`
- **fn** [[eos_ai-orchestrator-py-refresh_ambient_state]]`(ctx) → None`
- **fn** [[eos_ai-orchestrator-py-start_ambient_refresh_loop]]`(ctx) → None`

## Import Statements

```python
import json
import os
import sys
import datetime
from pathlib import Path
import requests
from dotenv import load_dotenv
from eos_ai.agent_runtime import AgentRuntime
from eos_ai.agent_runtime import TaskType
from eos_ai.context import EOSContext
from eos_ai.db import get_conn
from eos_ai.db import resolve_venture
from eos_ai.memory import AgentMemory
from eos_ai.venture_knowledge import VentureKnowledgeBase
```
