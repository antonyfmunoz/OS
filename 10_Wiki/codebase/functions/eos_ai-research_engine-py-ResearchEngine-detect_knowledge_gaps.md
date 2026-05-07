---
type: codebase-function
file: eos_ai/research_engine.py
line: 61
generated: 2026-05-07
---

# ResearchEngine.detect_knowledge_gaps

**File:** [[eos_ai-research_engine-py]] | **Line:** 61
**Signature:** `detect_knowledge_gaps() → list[str]`

**Class:** [[eos_ai-research_engine-py-ResearchEngine]]

Query interaction history for patterns where deeper knowledge would
have produced better outputs. Use CognitiveLoop to identify the gaps.

Falls back to foundational gap detection when no interaction history
exists yet (common in early-stage deployments).
...

## Calls

- [[eos_ai-research_engine-py-ResearchEngine-_detect_foundational_gaps]]
- [[eos_ai-research_engine-py-ResearchEngine-_query_local_interactions]]
- [[eos_ai-research_engine-py-ResearchEngine-_query_neon_interactions]]

## Called By

- [[eos_ai-research_engine-py-ResearchEngine-run_gap_fill_cycle]]
