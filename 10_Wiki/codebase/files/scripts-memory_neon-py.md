---
type: codebase-file
path: scripts/memory_neon.py
module: scripts.memory_neon
lines: 565
size: 18307
generated: 2026-04-11
---

# scripts/memory_neon.py

Neon integration helpers for the memory pipeline.

Thin wrappers around AgentMemory.log_event() and KnowledgeGraph.link_entities().
All calls are try/except guarded — Neon is enhancement, never blocking.

...

**Lines:** 565 | **Size:** 18,307 bytes

## Depends On

- [[eos_ai-db-py]]

## Contains

- **fn** [[scripts-memory_neon-py-record_summary_created]]`(session_id, summary_path, title, topics, model_used, provider, salience_score, salience_label, salience_reasons) → None`
- **fn** [[scripts-memory_neon-py-record_wiki_promoted]]`(wiki_path, wiki_slug, page_type, source_summary_path, source_session_id, salience_score, salience_label) → None`
- **fn** [[scripts-memory_neon-py-_link]]`(from_type, from_id, to_type, to_id, relationship) → None`
- **fn** [[scripts-memory_neon-py-_path_to_slug]]`(path) → str`
- **fn** [[scripts-memory_neon-py-search_memory_events]]`(query, event_type, date_from, date_to, salience_label, limit) → list[dict]`
- **fn** [[scripts-memory_neon-py-search_summaries]]`(query, topic, salience_label, date_from, date_to, promoted, limit) → list[dict]`
- **fn** [[scripts-memory_neon-py-get_related_sessions]]`(entity_id, entity_type, relationship, limit) → list[dict]`
- **fn** [[scripts-memory_neon-py-get_recurring_themes]]`(window_days, min_occurrences, limit) → list[dict]`
- **fn** [[scripts-memory_neon-py-_get_promoted_summary_slugs]]`() → set[str]`
- **fn** [[scripts-memory_neon-py-ensure_indexes]]`() → None`

## Import Statements

```python
import sys
import logging
from eos_ai.db import get_conn
from eos_ai.db import ORG_ID
```
