---
type: codebase-function
file: eos_ai/research_engine.py
line: 602
generated: 2026-05-07
---

# ResearchEngine.run_domain_update_cycle

**File:** [[eos_ai-research_engine-py]] | **Line:** 602
**Signature:** `run_domain_update_cycle() → dict`

**Class:** [[eos_ai-research_engine-py-ResearchEngine]]

Weekly domain update cycle. Horizontal-then-vertical methodology:

1. HORIZONTAL SCAN — ask Haiku to rate significance (1-10) for every
   domain that is due for update. One cheap call per domain.
2. VERTICAL DEPTH — research top 5 highest-scoring domains in full
...

## Calls

- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-get]]
