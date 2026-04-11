---
type: codebase-function
file: eos_ai/knowledge_domains.py
line: 977
generated: 2026-04-11
---

# KnowledgeDomainRegistry.get_update_schedule

**File:** [[eos_ai-knowledge_domains-py]] | **Line:** 977
**Signature:** `get_update_schedule() → list[str]`

**Class:** [[eos_ai-knowledge_domains-py-KnowledgeDomainRegistry]]

Return domain keys that are due for an update based on
update_frequency and the last_updated timestamp in current state.
Domains with no recorded state are always due.

## Called By

- [[eos_ai-knowledge_domains-py-KnowledgeDomainRegistry-get_status_report]]
