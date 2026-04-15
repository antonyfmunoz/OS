---
type: codebase-function
file: eos_ai/evolution_engine.py
line: 431
generated: 2026-04-12
---

# EvolutionEngine.propose_workflow_improvement

**File:** [[eos_ai-evolution_engine-py]] | **Line:** 431
**Signature:** `propose_workflow_improvement(workflow_id) → dict`

**Class:** [[eos_ai-evolution_engine-py-EvolutionEngine]]

Load workflow from Neon, analyze execution history, and propose
an improved version using Musk's Law (question every step, delete
unnecessary ones, simplify, accelerate).

Does NOT auto-apply — queues for founder approval.
...

## Calls

- [[eos_ai-agent_runtime-py-AgentRuntime-run]]
- [[eos_ai-cognitive_loop-py-CognitiveLoop-run]]
- [[eos_ai-db-py-get_conn]]

## Called By

- [[eos_ai-evolution_engine-py-EvolutionEngine-run_weekly_evolution_cycle]]
