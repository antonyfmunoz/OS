---
type: codebase-file
path: eos_ai/db.py
module: eos_ai.db
lines: 124
size: 4464
tags: [critical]
generated: 2026-04-12
---

# eos_ai/db.py

> **CRITICAL FILE** — Core infrastructure. Read before modifying.

Neon (PostgreSQL) connection layer for the Python AI layer.

RLS pattern: every transaction opens with
    SET LOCAL app.current_org_id = '<org_uuid>'
matching the saas pattern exactly — one Postgres instance, one RLS
...

**Lines:** 124 | **Size:** 4,464 bytes

## Used By

- [[core-execution_contract-py]]
- [[eos_ai-authority_engine-py]]
- [[eos_ai-context_compaction-py]]
- [[eos_ai-coordination_engine-py]]
- [[eos_ai-event_bus-py]]
- [[eos_ai-evolution_engine-py]]
- [[eos_ai-execution_engine-py]]
- [[eos_ai-gateway-py]]
- [[eos_ai-higgsfield_client-py]]
- [[eos_ai-human_intelligence-py]]
- [[eos_ai-knowledge_graph-py]]
- [[eos_ai-memory-py]]
- [[eos_ai-model_preferences-py]]
- [[eos_ai-orchestrator-py]]
- [[eos_ai-portfolio_advisor-py]]
- [[eos_ai-research_engine-py]]
- [[eos_ai-status-py]]
- [[eos_ai-strategy_engine-py]]
- [[eos_ai-user_model-py]]
- [[eos_ai-venture_knowledge-py]]
- [[scripts-higgsfield_smoke_test-py]]
- [[scripts-memory_neon-py]]
- [[scripts-sync_skills_to_neon-py]]
- [[scripts-test_execution_contract-py]]
- [[services-higgsfield_webhook-py]]

## Contains

- **fn** [[eos_ai-db-py-_load_caches]]`(cur) → None`
- **fn** [[eos_ai-db-py-get_conn]]`(org_id) → Generator`
- **fn** [[eos_ai-db-py-resolve_venture]]`(slug) → str | None`
- **fn** [[eos_ai-db-py-resolve_skill]]`(name) → str | None`

## Import Statements

```python
import os
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
```
