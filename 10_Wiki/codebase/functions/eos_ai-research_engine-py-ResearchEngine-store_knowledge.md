---
type: codebase-function
file: eos_ai/research_engine.py
line: 342
generated: 2026-04-12
---

# ResearchEngine.store_knowledge

**File:** [[eos_ai-research_engine-py]] | **Line:** 342
**Signature:** `store_knowledge(topic, knowledge_object, venture_id) → bool`

**Class:** [[eos_ai-research_engine-py-ResearchEngine]]

Write a research result to the Neon skills table as a permanent
knowledge skill. Skill names follow the pattern: knowledge_{topic_slug}.

The SkillRegistry loads DB skills on init — this knowledge is injected
into future relevant agent calls automatically.
...

## Calls

- [[eos_ai-db-py-get_conn]]
- [[eos_ai-memory-py-AgentMemory-log_event]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-get]]

## Called By

- [[eos_ai-research_engine-py-ResearchEngine-run_gap_fill_cycle]]
