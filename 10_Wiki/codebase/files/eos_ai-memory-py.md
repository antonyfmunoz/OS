---
type: codebase-file
path: eos_ai/memory.py
module: eos_ai.memory
lines: 1019
size: 40118
tags: [critical]
generated: 2026-05-07
---

# eos_ai/memory.py

> **CRITICAL FILE** — Core infrastructure. Read before modifying.

Persistent memory for OS agents — backed by Neon (PostgreSQL).

Unified data layer: Python AI layer and TypeScript SaaS backend write to the
same Postgres instance through the same RLS firewall. SQLite is gone.

...

**Lines:** 1019 | **Size:** 40,118 bytes

## Depends On

- [[eos_ai-db-py]]

## Used By

- [[eos_ai-integration_test-py]]
- [[eos_ai-knowledge_integrator-py]]
- [[eos_ai-reality_engine-py]]
- [[eos_ai-research_engine-py]]
- [[eos_ai-status-py]]
- [[eos_ai-strategy_engine-py]]
- [[services-calendly_webhook-py]]
- [[services-icp_scorer-py]]

## Contains

- **class** [[eos_ai-memory-py-AgentMemory]] — 14 methods
- **class** [[eos_ai-memory-py-Message]] — 0 methods
- **class** [[eos_ai-memory-py-ConversationMemory]] — 10 methods
- **fn** [[eos_ai-memory-py-_utcnow]]`() → str`
- **fn** [[eos_ai-memory-py-_tokens_to_neon]]`(tokens_json) → dict`

## Import Statements

```python
import json
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import TYPE_CHECKING
from eos_ai.db import get_conn
from eos_ai.db import resolve_venture
from eos_ai.db import resolve_skill
from eos_ai.db import ORG_ID
from eos_ai.db import USER_ID
import uuid as _uuid
from dataclasses import dataclass as _dataclass
from typing import Optional as _Optional
```
