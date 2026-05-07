---
type: codebase-function
file: scripts/memory_neon.py
line: 74
generated: 2026-05-07
---

# record_wiki_promoted

**File:** [[scripts-memory_neon-py]] | **Line:** 74
**Signature:** `record_wiki_promoted(wiki_path, wiki_slug, page_type, source_summary_path, source_session_id, salience_score, salience_label) → None`

Record a wiki promotion event and link wiki page to its sources.

1. events: event_type='memory_wiki_promoted'
2. entity_links: wiki_page → summary (promoted_from)
3. entity_links: wiki_page → conversation (sourced_from) if session_id available

## Calls

- [[eos_ai-db-py-get_conn]]
- [[scripts-memory_neon-py-_link]]
- [[scripts-memory_neon-py-_path_to_slug]]
