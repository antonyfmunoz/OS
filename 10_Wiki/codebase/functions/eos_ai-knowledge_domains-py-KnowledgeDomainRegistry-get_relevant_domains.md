---
type: codebase-function
file: eos_ai/knowledge_domains.py
line: 912
generated: 2026-04-12
---

# KnowledgeDomainRegistry.get_relevant_domains

**File:** [[eos_ai-knowledge_domains-py]] | **Line:** 912
**Signature:** `get_relevant_domains(context, task_type, top_n) → list[dict]`

**Class:** [[eos_ai-knowledge_domains-py-KnowledgeDomainRegistry]]

Score each domain by trigger-word matches against context and task_type.
Returns top_n domains sorted by relevance score, each as:
    {key, category, core_principles, relevance_score, current_state?}
