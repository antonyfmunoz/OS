---
type: codebase-class
file: eos_ai/input_intelligence.py
line: 103
generated: 2026-04-12
---

# InputIntelligence

**File:** [[eos_ai-input_intelligence-py]] | **Line:** 103

Gateway-level input intelligence layer.
Processes every agent_task request before it reaches the cognitive loop.

## Methods

- [[eos_ai-input_intelligence-py-InputIntelligence-__init__]]`(ctx, venture_id)` — 
- [[eos_ai-input_intelligence-py-InputIntelligence-process]]`(prompt, venture_id) → EnhancedInput` — Main entry point. Assess and optionally enhance the input.
- [[eos_ai-input_intelligence-py-InputIntelligence-_assess]]`(prompt) → InputAssessment` — Determine the signal type and whether enhancement is warranted.
- [[eos_ai-input_intelligence-py-InputIntelligence-_is_greeting]]`(normalized) → bool` — Check if the input is a greeting or human moment.
- [[eos_ai-input_intelligence-py-InputIntelligence-_is_status_check]]`(normalized) → bool` — Check if the input is a status check that's already clear.
- [[eos_ai-input_intelligence-py-InputIntelligence-_has_business_signal]]`(normalized) → bool` — Check if the input contains business-relevant language.
- [[eos_ai-input_intelligence-py-InputIntelligence-_enhance]]`(prompt, assessment, venture_id) → str` — Elevate an underpowered input to a world-class execution prompt.
- [[eos_ai-input_intelligence-py-InputIntelligence-_get_venture_context]]`(venture_id) → str` — Build a compact venture context string for the enhancement prompt.
