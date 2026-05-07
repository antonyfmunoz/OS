---
type: codebase-class
file: eos_ai/principle_engine.py
line: 349
generated: 2026-05-07
---

# PrincipleEngine

**File:** [[eos_ai-principle_engine-py]] | **Line:** 349

Injects the root rule and domain-relevant principles into every AI task.

Usage:
    pe = PrincipleEngine(ctx)
    principles = pe.get_relevant_principles('sales', 'lyfe_institute')
...

## Methods

- [[eos_ai-principle_engine-py-PrincipleEngine-__init__]]`(ctx) → None` — 
- [[eos_ai-principle_engine-py-PrincipleEngine-get_relevant_principles]]`(task_type, venture_id) → list[str]` — Return principles relevant to the task type.
- [[eos_ai-principle_engine-py-PrincipleEngine-format_for_prompt]]`(task_type, venture_id) → str` — Return principles formatted as a prompt block for injection into AI calls.
- [[eos_ai-principle_engine-py-PrincipleEngine-get_root_rule]]`() → str` — Return the permanent root rule.
- [[eos_ai-principle_engine-py-PrincipleEngine-list_domains]]`() → list[str]` — Return all available principle domains.
- [[eos_ai-principle_engine-py-PrincipleEngine-get_universal_standards]]`() → str` — Return the full EOS operating framework:
- [[eos_ai-principle_engine-py-PrincipleEngine-get_agent_standards]]`(agent_id) → list[str]` — Get operational standards for a specific agent.
- [[eos_ai-principle_engine-py-PrincipleEngine-format_agent_standards]]`(agent_id) → str` — Format agent standards as injectable prompt block.
