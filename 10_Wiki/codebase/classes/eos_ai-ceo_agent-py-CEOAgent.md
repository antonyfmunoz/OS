---
type: codebase-class
file: eos_ai/ceo_agent.py
line: 37
generated: 2026-05-07
---

# CEOAgent

**File:** [[eos_ai-ceo_agent-py]] | **Line:** 37

Strategy layer. One instance per company.
Reports to Portfolio Agent. Directs EA Agent and all role agents.

Never executes — reasons and directs.
Never asks the founder for info it can find itself.

## Methods

- [[eos_ai-ceo_agent-py-CEOAgent-__init__]]`(ctx) → None` — 
- [[eos_ai-ceo_agent-py-CEOAgent-detect_primitives]]`() → dict` — Read all available context from Neon automatically.
- [[eos_ai-ceo_agent-py-CEOAgent-reason_org_chart]]`(primitives) → list[str]` — AI-powered org chart reasoning.
- [[eos_ai-ceo_agent-py-CEOAgent-evaluate_stage_transition]]`(primitives) → bool` — Check whether the company has crossed a stage upgrade threshold.
- [[eos_ai-ceo_agent-py-CEOAgent-spin_up_org]]`(primitives) → dict` — Configure org chart for the current stage.
- [[eos_ai-ceo_agent-py-CEOAgent-check_and_evolve]]`() → dict` — Full evolution cycle.
- [[eos_ai-ceo_agent-py-CEOAgent-get_active_constraint]]`(venture_id) → dict` — Active constraint from live data.
- [[eos_ai-ceo_agent-py-CEOAgent-generate_brief]]`(venture_id, venture_name) → str` — Generate CEO intelligence brief.
