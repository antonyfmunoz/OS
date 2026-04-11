---
type: codebase-function
file: eos_ai/evolution_engine.py
line: 685
generated: 2026-04-11
---

# EvolutionEngine.detect_new_agent_patterns

**File:** [[eos_ai-evolution_engine-py]] | **Line:** 685
**Signature:** `detect_new_agent_patterns() → list[dict]`

**Class:** [[eos_ai-evolution_engine-py-EvolutionEngine]]

Find task patterns repeated 10+ times in the last 30 days with no
matched agent (agent_label is null or default).
Returns list of {task_type, agent, count, description}.

## Calls

- [[eos_ai-db-py-get_conn]]

## Called By

- [[eos_ai-evolution_engine-py-EvolutionEngine-run_weekly_evolution_cycle]]
