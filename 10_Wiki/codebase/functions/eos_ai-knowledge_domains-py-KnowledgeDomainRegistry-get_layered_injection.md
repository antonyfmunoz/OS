---
type: codebase-function
file: eos_ai/knowledge_domains.py
line: 1064
generated: 2026-04-12
---

# KnowledgeDomainRegistry.get_layered_injection

**File:** [[eos_ai-knowledge_domains-py]] | **Line:** 1064
**Signature:** `get_layered_injection(domain_key, task_type, context) → str`

**Class:** [[eos_ai-knowledge_domains-py-KnowledgeDomainRegistry]]

Select and format the most relevant layers for this task type.
Returns a compact string for direct system-prompt injection.

Always includes: timeless principles
Adds tactical for: execute, outreach, close, generate
...
