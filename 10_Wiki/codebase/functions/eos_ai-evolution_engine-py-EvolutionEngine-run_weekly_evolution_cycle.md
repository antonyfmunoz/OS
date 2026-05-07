---
type: codebase-function
file: eos_ai/evolution_engine.py
line: 736
generated: 2026-05-07
---

# EvolutionEngine.run_weekly_evolution_cycle

**File:** [[eos_ai-evolution_engine-py]] | **Line:** 736
**Signature:** `run_weekly_evolution_cycle() → dict`

**Class:** [[eos_ai-evolution_engine-py-EvolutionEngine]]

Full weekly evolution cycle:
  1. analyze_system_performance()
  2. skill_improvement.run_improvement_cycle()
  3. research.run_gap_fill_cycle()
  4. Propose improvements for workflows with low performance
...

## Calls

- [[eos_ai-db-py-get_conn]]
- [[eos_ai-evolution_engine-py-EvolutionEngine-analyze_system_performance]]
- [[eos_ai-evolution_engine-py-EvolutionEngine-detect_new_agent_patterns]]
- [[eos_ai-evolution_engine-py-EvolutionEngine-propose_new_agent]]
- [[eos_ai-evolution_engine-py-EvolutionEngine-propose_workflow_improvement]]
- [[eos_ai-research_engine-py-ResearchEngine-run_gap_fill_cycle]]
- [[eos_ai-skill_improvement-py-SkillImprovementEngine-run_improvement_cycle]]
