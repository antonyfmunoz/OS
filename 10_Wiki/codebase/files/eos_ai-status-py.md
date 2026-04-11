---
type: codebase-file
path: eos_ai/status.py
module: eos_ai.status
lines: 330
size: 11123
tags: [entry-point]
generated: 2026-04-11
---

# eos_ai/status.py

> **ENTRY POINT** — Contains `if __name__` or server start.

EOS Status Dashboard — daily health check for the AI system.

Usage:
    python3 /opt/OS/eos_ai/status.py

**Lines:** 330 | **Size:** 11,123 bytes

## Depends On

- [[eos_ai-db-py]]
- [[eos_ai-memory-py]]
- [[eos_ai-skill_registry-py]]
- [[eos_ai-venture_knowledge-py]]

## Contains

- **fn** [[eos_ai-status-py-_bar]]`(pct, width) → str`
- **fn** [[eos_ai-status-py-_fmt_tokens]]`(n) → str`
- **fn** [[eos_ai-status-py-_cost_est]]`(interactions_7d) → float`
- **fn** [[eos_ai-status-py-_fetch_7d_raw]]`() → list[dict]`
- **fn** [[eos_ai-status-py-_fetch_skill_outcome_counts]]`() → dict[str, int]`
- **fn** [[eos_ai-status-py-_fetch_reply_rates]]`() → list[dict]`
- **fn** [[eos_ai-status-py-_fetch_total_interactions]]`() → int`
- **fn** [[eos_ai-status-py-_fetch_last_orchestrator_run]]`() → dict | None`
- **fn** [[eos_ai-status-py-_get_last_brief_excerpt]]`() → str | None`
- **fn** [[eos_ai-status-py-_section_north_star]]`() → None`
- **fn** [[eos_ai-status-py-_section_7d_activity]]`(rows_7d) → None`
- **fn** [[eos_ai-status-py-_section_skill_performance]]`(reply_rates, outcome_counts) → None`
- **fn** [[eos_ai-status-py-_section_last_orchestrator]]`(orch_row, excerpt) → None`
- **fn** [[eos_ai-status-py-_section_memory]]`(total_interactions) → None`
- **fn** [[eos_ai-status-py-_section_skill_readiness]]`(outcome_counts, registry) → None`
- **fn** [[eos_ai-status-py-main]]`() → None`

## Import Statements

```python
import json
import os
import sys
import datetime
from pathlib import Path
from dotenv import load_dotenv
from eos_ai.db import get_conn
from eos_ai.db import ORG_ID
from eos_ai.memory import AgentMemory
from eos_ai.venture_knowledge import VentureKnowledgeBase
from eos_ai.skill_registry import SkillRegistry
```
