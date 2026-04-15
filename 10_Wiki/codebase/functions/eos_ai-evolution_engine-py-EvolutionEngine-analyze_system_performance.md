---
type: codebase-function
file: eos_ai/evolution_engine.py
line: 270
generated: 2026-04-12
---

# EvolutionEngine.analyze_system_performance

**File:** [[eos_ai-evolution_engine-py]] | **Line:** 270
**Signature:** `analyze_system_performance() → dict`

**Class:** [[eos_ai-evolution_engine-py-EvolutionEngine]]

Query last 30 days of interactions, outcomes, and events from Neon.

Calculates:
    overall_reply_rate:       float | None   — reply outcomes / total outcomes
    avg_iterations_per_task:  float          — from cognitive_reflection events
...

## Calls

- [[eos_ai-db-py-get_conn]]

## Called By

- [[eos_ai-evolution_engine-py-EvolutionEngine-run_weekly_evolution_cycle]]
