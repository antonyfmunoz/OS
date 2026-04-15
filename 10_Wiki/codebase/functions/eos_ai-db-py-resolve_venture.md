---
type: codebase-function
file: eos_ai/db.py
line: 96
generated: 2026-04-12
---

# resolve_venture

**File:** [[eos_ai-db-py]] | **Line:** 96
**Signature:** `resolve_venture(slug) → str | None`

Map a Python venture slug to its Neon UUID.

Slugs are derived from venture names: lowercase, spaces → underscores.
e.g. "Lyfe Institute" → "lyfe_institute" → "<uuid>"

...

## Called By

- [[eos_ai-coordination_engine-py-CoordinationEngine-assign_task]]
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-_store_profile]]
- [[eos_ai-knowledge_graph-py-KnowledgeGraph-find_patterns]]
- [[eos_ai-memory-py-AgentMemory-get_interaction_for_lead]]
- [[eos_ai-memory-py-AgentMemory-get_recent]]
- [[eos_ai-memory-py-AgentMemory-log]]
- [[eos_ai-memory-py-AgentMemory-log_lead_scored]]
- [[eos_ai-memory-py-AgentMemory-semantic_search]]
- [[eos_ai-orchestrator-py-EOSOrchestrator-_query_7d_stats]]
- [[eos_ai-strategy_engine-py-_query_30d_stats]]
