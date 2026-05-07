---
type: codebase-function
file: eos_ai/knowledge_integrator.py
line: 69
generated: 2026-05-07
---

# KnowledgeIntegrator.integrate

**File:** [[eos_ai-knowledge_integrator-py]] | **Line:** 69
**Signature:** `integrate(content, source, category, metadata) → bool`

**Class:** [[eos_ai-knowledge_integrator-py-KnowledgeIntegrator]]

Permanently store new knowledge.

Stores as an interaction row (not events) so the FK on the embeddings
table is satisfied and semantic_search() returns results correctly.
Also logs to the events table for audit trail.
...

## Calls

- [[eos_ai-embedding_engine-py-EmbeddingEngine-embed_interaction]]
- [[eos_ai-embedding_engine-py-EmbeddingEngine-is_available]]
- [[eos_ai-memory-py-AgentMemory-log_event]]

## Called By

- [[eos_ai-knowledge_integrator-py-KnowledgeIntegrator-integrate_creator_content]]
- [[eos_ai-knowledge_integrator-py-KnowledgeIntegrator-integrate_search_result]]
- [[eos_ai-knowledge_integrator-py-KnowledgeIntegrator-integrate_world_event]]
- [[eos_ai-world_pulse-py-WorldPulse-run_market_intel_scan]]
- [[eos_ai-world_pulse-py-WorldPulse-run_pulse_scan]]
