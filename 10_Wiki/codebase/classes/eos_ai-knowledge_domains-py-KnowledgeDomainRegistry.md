---
type: codebase-class
file: eos_ai/knowledge_domains.py
line: 818
generated: 2026-04-12
---

# KnowledgeDomainRegistry

**File:** [[eos_ai-knowledge_domains-py]] | **Line:** 818

Structured awareness of every domain the system operates in.

On init, loads any previously saved domain state from the Neon skills
table. On query, scores domains by trigger-word match and returns the
top N most relevant domains with their core principles.

## Methods

- [[eos_ai-knowledge_domains-py-KnowledgeDomainRegistry-__init__]]`()` — 
- [[eos_ai-knowledge_domains-py-KnowledgeDomainRegistry-_load_state]]`() → dict` — Load domain current_state from Neon skills table (domain_ prefix).
- [[eos_ai-knowledge_domains-py-KnowledgeDomainRegistry-save_domain_update]]`(domain_key, current_state, ctx) → bool` — Persist updated domain knowledge to the Neon skills table
- [[eos_ai-knowledge_domains-py-KnowledgeDomainRegistry-get_domain]]`(key) → dict | None` — Return the static domain definition for a given key.
- [[eos_ai-knowledge_domains-py-KnowledgeDomainRegistry-all_domains]]`() → list[str]` — Return all registered domain keys.
- [[eos_ai-knowledge_domains-py-KnowledgeDomainRegistry-get_relevant_domains]]`(context, task_type, top_n) → list[dict]` — Score each domain by trigger-word matches against context and task_type.
- [[eos_ai-knowledge_domains-py-KnowledgeDomainRegistry-format_for_injection]]`(domains) → str` — Format domain knowledge for system prompt injection.
- [[eos_ai-knowledge_domains-py-KnowledgeDomainRegistry-get_update_schedule]]`() → list[str]` — Return domain keys that are due for an update based on
- [[eos_ai-knowledge_domains-py-KnowledgeDomainRegistry-get_layered_context]]`(domain_key, layers_needed) → str` — Return formatted context from specified layers of a domain.
- [[eos_ai-knowledge_domains-py-KnowledgeDomainRegistry-get_layered_injection]]`(domain_key, task_type, context) → str` — Select and format the most relevant layers for this task type.
- [[eos_ai-knowledge_domains-py-KnowledgeDomainRegistry-get_status_report]]`() → str` — Human-readable status of all domains — for /domains Telegram command.
