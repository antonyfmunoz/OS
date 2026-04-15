---
type: codebase-function
file: eos_ai/orchestrator.py
line: 1282
generated: 2026-04-12
---

# EOSOrchestrator.morning_brief

**File:** [[eos_ai-orchestrator-py]] | **Line:** 1282
**Signature:** `morning_brief() → str`

**Class:** [[eos_ai-orchestrator-py-EOSOrchestrator]]

DEPRECATED: Use run_full_morning_cycle() instead.

Generate a structured AI brief, write it to orchestrator/daily/,
and return the full text.

## Calls

- [[eos_ai-agent_runtime-py-AgentRuntime-run]]
- [[eos_ai-orchestrator-py-EOSOrchestrator-_query_7d_stats]]
- [[eos_ai-orchestrator-py-EOSOrchestrator-get_north_star_status]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-list_ventures]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-to_agent_context]]

## Called By

- [[eos_ai-orchestrator-py-EOSOrchestrator-run_morning_cycle]]
