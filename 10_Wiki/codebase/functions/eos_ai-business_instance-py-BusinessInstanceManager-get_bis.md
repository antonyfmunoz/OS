---
type: codebase-function
file: eos_ai/business_instance.py
line: 278
generated: 2026-04-11
---

# BusinessInstanceManager.get_bis

**File:** [[eos_ai-business_instance-py]] | **Line:** 278
**Signature:** `get_bis(venture_id) → Optional[BusinessInstance]`

**Class:** [[eos_ai-business_instance-py-BusinessInstanceManager]]

Load BIS from ventures.config_json. Returns None if not found.

## Called By

- [[eos_ai-business_instance-py-BusinessInstanceManager-advance_stage]]
- [[eos_ai-business_instance-py-BusinessInstanceManager-format_full_summary]]
- [[eos_ai-business_instance-py-BusinessInstanceManager-get_context_for_agents]]
- [[eos_ai-business_instance-py-BusinessInstanceManager-get_stage_guidance]]
- [[eos_ai-business_instance-py-get_ai_name]]
