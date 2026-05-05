---
type: codebase-class
file: eos_ai/knowledge_integrator.py
line: 58
generated: 2026-04-12
---

# KnowledgeIntegrator

**File:** [[eos_ai-knowledge_integrator-py]] | **Line:** 58

Permanently integrates new knowledge into the system.
Every call to integrate() stores to Neon events AND embeds for semantic retrieval.
Never overwrites — always adds. Degrades gracefully on any failure.

## Methods

- [[eos_ai-knowledge_integrator-py-KnowledgeIntegrator-__init__]]`(ctx)` — 
- [[eos_ai-knowledge_integrator-py-KnowledgeIntegrator-integrate]]`(content, source, category, metadata) → bool` — Permanently store new knowledge.
- [[eos_ai-knowledge_integrator-py-KnowledgeIntegrator-integrate_search_result]]`(query, results) → int` — Integrate all pages from a web search permanently.
- [[eos_ai-knowledge_integrator-py-KnowledgeIntegrator-integrate_creator_content]]`(creator, title, content, url) → bool` — Store content from a known creator permanently.
- [[eos_ai-knowledge_integrator-py-KnowledgeIntegrator-integrate_world_event]]`(event, context, source) → bool` — Store a significant world event permanently.
- [[eos_ai-knowledge_integrator-py-KnowledgeIntegrator-query_knowledge]]`(query, limit) → list[dict]` — Semantic search across all stored knowledge.
