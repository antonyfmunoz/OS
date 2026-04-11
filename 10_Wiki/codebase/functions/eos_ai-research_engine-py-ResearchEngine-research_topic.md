---
type: codebase-function
file: eos_ai/research_engine.py
line: 226
generated: 2026-04-11
---

# ResearchEngine.research_topic

**File:** [[eos_ai-research_engine-py]] | **Line:** 226
**Signature:** `research_topic(topic, venture_id) → dict`

**Class:** [[eos_ai-research_engine-py-ResearchEngine]]

Horizontal research on a topic using live web sources via Scrapling,
grounded in primary evidence rather than model priors alone.

Returns:
    topic, venture_id, summary, confidence, sources_quality,
...

## Calls

- [[eos_ai-agent_runtime-py-AgentRuntime-run]]
- [[eos_ai-cognitive_loop-py-CognitiveLoop-run]]
- [[eos_ai-strategy_engine-py-_parse_labeled_sections]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-get]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-to_agent_context]]

## Called By

- [[eos_ai-research_engine-py-ResearchEngine-run_gap_fill_cycle]]
