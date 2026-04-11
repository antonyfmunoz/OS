---
type: codebase-function
file: eos_ai/evolution_engine.py
line: 591
generated: 2026-04-11
---

# EvolutionEngine.propose_new_agent

**File:** [[eos_ai-evolution_engine-py]] | **Line:** 591
**Signature:** `propose_new_agent(pattern_description) → dict`

**Class:** [[eos_ai-evolution_engine-py-EvolutionEngine]]

If a task pattern repeats 10+ times with no matching agent, propose
a new sub-agent. Queues proposal to approvals table.
Founder approves → agent row inserted to Neon.

Returns:
...

## Calls

- [[eos_ai-agent_runtime-py-AgentRuntime-run]]
- [[eos_ai-cognitive_loop-py-CognitiveLoop-run]]
- [[eos_ai-db-py-get_conn]]

## Called By

- [[eos_ai-evolution_engine-py-EvolutionEngine-run_weekly_evolution_cycle]]
