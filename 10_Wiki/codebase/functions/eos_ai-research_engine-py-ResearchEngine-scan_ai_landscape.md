---
type: codebase-function
file: eos_ai/research_engine.py
line: 478
generated: 2026-04-11
---

# ResearchEngine.scan_ai_landscape

**File:** [[eos_ai-research_engine-py]] | **Line:** 478
**Signature:** `scan_ai_landscape() → dict`

**Class:** [[eos_ai-research_engine-py-ResearchEngine]]

Horizontal scan of the current AI landscape.
Uses Perplexity for real-time data if PERPLEXITY_API_KEY is set,
falls back to Sonnet otherwise.
Stores result as domain_technology_ai in Neon skills table.
Updates COST_PER_MILLION_TOKENS in-memory for this session.

## Calls

- [[eos_ai-agent_runtime-py-AgentRuntime-run]]
- [[eos_ai-cognitive_loop-py-CognitiveLoop-run]]
- [[eos_ai-research_engine-py-ResearchEngine-_parse_model_costs]]
