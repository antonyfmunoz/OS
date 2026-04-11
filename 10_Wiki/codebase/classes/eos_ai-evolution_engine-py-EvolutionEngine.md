---
type: codebase-class
file: eos_ai/evolution_engine.py
line: 136
generated: 2026-04-11
---

# EvolutionEngine

**File:** [[eos_ai-evolution_engine-py]] | **Line:** 136

Continuous improvement layer. Analyzes system performance, proposes
workflow improvements and new agents, and orchestrates the weekly
evolution cycle.

## Methods

- [[eos_ai-evolution_engine-py-EvolutionEngine-__init__]]`(ctx)` — 
- [[eos_ai-evolution_engine-py-EvolutionEngine-_get_stage]]`(venture_id) → int` — Read BIS stage for venture. Returns 1 on any failure (safe default).
- [[eos_ai-evolution_engine-py-EvolutionEngine-get_current_stage]]`(venture_id) → int` — Return the current BIS stage integer for a venture.
- [[eos_ai-evolution_engine-py-EvolutionEngine-get_active_primitives]]`(venture_id) → list[str]` — Return list of primitive IDs that are active (applies=True) at the
- [[eos_ai-evolution_engine-py-EvolutionEngine-is_primitive_unlocked]]`(primitive_id, venture_id) → dict` — Check whether a primitive applies at the venture's current stage.
- [[eos_ai-evolution_engine-py-EvolutionEngine-check_prerequisites]]`(primitive_id, venture_id) → dict` — Check whether the prerequisites for a primitive are met.
- [[eos_ai-evolution_engine-py-EvolutionEngine-analyze_system_performance]]`() → dict` — Query last 30 days of interactions, outcomes, and events from Neon.
- [[eos_ai-evolution_engine-py-EvolutionEngine-propose_workflow_improvement]]`(workflow_id) → dict` — Load workflow from Neon, analyze execution history, and propose
- [[eos_ai-evolution_engine-py-EvolutionEngine-propose_new_agent]]`(pattern_description) → dict` — If a task pattern repeats 10+ times with no matching agent, propose
- [[eos_ai-evolution_engine-py-EvolutionEngine-detect_new_agent_patterns]]`() → list[dict]` — Find task patterns repeated 10+ times in the last 30 days with no
- [[eos_ai-evolution_engine-py-EvolutionEngine-run_weekly_evolution_cycle]]`() → dict` — Full weekly evolution cycle:
- [[eos_ai-evolution_engine-py-EvolutionEngine-format_performance_report]]`(perf) → str` — Format analyze_system_performance() result for Telegram.
- [[eos_ai-evolution_engine-py-EvolutionEngine-format_evolution_summary]]`(summary) → str` — Format run_weekly_evolution_cycle() result for Telegram.
