---
type: codebase-function
file: scripts/memory_neon.py
line: 24
generated: 2026-04-12
---

# record_summary_created

**File:** [[scripts-memory_neon-py]] | **Line:** 24
**Signature:** `record_summary_created(session_id, summary_path, title, topics, model_used, provider, salience_score, salience_label, salience_reasons) → None`

Record a summary creation event and link it to its source conversation.

1. events: event_type='memory_summary_created'
2. entity_links: summary → conversation (summarizes)

## Calls

- [[eos_ai-db-py-get_conn]]
- [[scripts-memory_neon-py-_link]]
- [[scripts-memory_neon-py-_path_to_slug]]
