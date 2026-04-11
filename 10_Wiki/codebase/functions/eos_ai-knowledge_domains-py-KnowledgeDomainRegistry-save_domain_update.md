---
type: codebase-function
file: eos_ai/knowledge_domains.py
line: 855
generated: 2026-04-11
---

# KnowledgeDomainRegistry.save_domain_update

**File:** [[eos_ai-knowledge_domains-py]] | **Line:** 855
**Signature:** `save_domain_update(domain_key, current_state, ctx) → bool`

**Class:** [[eos_ai-knowledge_domains-py-KnowledgeDomainRegistry]]

Persist updated domain knowledge to the Neon skills table
as a skill named domain_{key}. Returns True on success.
