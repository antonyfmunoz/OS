---
type: codebase-class
file: eos_ai/substrate/rituals.py
line: 93
generated: 2026-04-11
---

# RitualRegistry

**File:** [[eos_ai-substrate-rituals-py]] | **Line:** 93

Persistent ritual tracker.

Rituals are flushed through eos_ai.substrate.storage on every lifecycle
transition so cron scripts running in separate processes can share state
(morning cron starts an open_day ritual; a later EA interaction can find
...

## Methods

- [[eos_ai-substrate-rituals-py-RitualRegistry-__init__]]`() → None` — 
- [[eos_ai-substrate-rituals-py-RitualRegistry-_load]]`() → None` — 
- [[eos_ai-substrate-rituals-py-RitualRegistry-_flush]]`() → None` — 
- [[eos_ai-substrate-rituals-py-RitualRegistry-default]]`() → 'RitualRegistry'` — 
- [[eos_ai-substrate-rituals-py-RitualRegistry-reset_default_for_tests]]`() → None` — 
- [[eos_ai-substrate-rituals-py-RitualRegistry-start]]`(kind, inputs) → Ritual` — 
- [[eos_ai-substrate-rituals-py-RitualRegistry-advance]]`(ritual_id, new_state) → Ritual` — 
- [[eos_ai-substrate-rituals-py-RitualRegistry-complete]]`(ritual_id, outputs) → Ritual` — 
- [[eos_ai-substrate-rituals-py-RitualRegistry-fail]]`(ritual_id, reason) → Ritual` — 
- [[eos_ai-substrate-rituals-py-RitualRegistry-get]]`(ritual_id) → Optional[Ritual]` — 
- [[eos_ai-substrate-rituals-py-RitualRegistry-active]]`(kind) → list[Ritual]` — 
- [[eos_ai-substrate-rituals-py-RitualRegistry-history]]`() → list[Ritual]` — 
- [[eos_ai-substrate-rituals-py-RitualRegistry-_require]]`(ritual_id) → Ritual` — 
