---
type: codebase-function
file: eos_ai/memory.py
line: 404
generated: 2026-05-07
---

# AgentMemory.log_event

**File:** [[eos_ai-memory-py]] | **Line:** 404
**Signature:** `log_event(org_id, event_type, payload) → str`

**Class:** [[eos_ai-memory-py-AgentMemory]]

Write a structured event to the Neon events table.
Used by CognitiveLoop for reflections and any
layer that needs to record a non-interaction event.
Returns event_id (UUID).

## Calls

- [[eos_ai-db-py-get_conn]]

## Called By

- [[eos_ai-knowledge_integrator-py-KnowledgeIntegrator-integrate]]
- [[eos_ai-reality_engine-py-RealityIntelligenceEngine-generate_truth_report]]
- [[eos_ai-reality_engine-py-RealityIntelligenceEngine-process_signal_queue]]
- [[eos_ai-research_engine-py-ResearchEngine-store_knowledge]]
- [[eos_ai-strategy_engine-py-DecisionEngine-evaluate]]
