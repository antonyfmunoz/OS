---
type: codebase-class
file: eos_ai/business_instance.py
line: 206
generated: 2026-05-07
---

# BusinessInstanceManager

**File:** [[eos_ai-business_instance-py]] | **Line:** 206

Persist and retrieve BusinessInstance data via the ventures table
config_json column. Provides stage guidance and agent context injection.

## Methods

- [[eos_ai-business_instance-py-BusinessInstanceManager-__init__]]`(ctx) → None` — 
- [[eos_ai-business_instance-py-BusinessInstanceManager-save_bis]]`(bis) → bool` — Persist BIS to ventures.config_json. Creates venture row if needed.
- [[eos_ai-business_instance-py-BusinessInstanceManager-get_default_venture_id]]`() → Optional[str]` — Return the default venture_id for the current org — substrate-neutral.
- [[eos_ai-business_instance-py-BusinessInstanceManager-get_bis]]`(venture_id) → Optional[BusinessInstance]` — Load BIS from ventures.config_json. Returns None if not found.
- [[eos_ai-business_instance-py-BusinessInstanceManager-get_stage_guidance]]`(venture_id) → dict` — Return stage-appropriate focus, actions, and proof gate.
- [[eos_ai-business_instance-py-BusinessInstanceManager-create_from_wizard]]`(answers) → 'BusinessInstance'` — Create a BusinessInstance from onboarding wizard answers dict.
- [[eos_ai-business_instance-py-BusinessInstanceManager-advance_stage]]`(venture_id, proof) → dict` — Advance venture to next stage if proof provided.
- [[eos_ai-business_instance-py-BusinessInstanceManager-get_context_for_agents]]`(venture_id) → str` — Return BIS context string for injection into agent system prompts.
- [[eos_ai-business_instance-py-BusinessInstanceManager-format_full_summary]]`(venture_id) → str` — Return full BIS summary for /bis Telegram command.
