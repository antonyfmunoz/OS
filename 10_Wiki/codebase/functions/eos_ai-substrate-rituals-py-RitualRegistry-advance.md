---
type: codebase-function
file: eos_ai/substrate/rituals.py
line: 174
generated: 2026-05-07
---

# RitualRegistry.advance

**File:** [[eos_ai-substrate-rituals-py]] | **Line:** 174
**Signature:** `advance(ritual_id, new_state) → Ritual`

**Class:** [[eos_ai-substrate-rituals-py-RitualRegistry]]

*No docstring.*

## Calls

- [[eos_ai-substrate-rituals-py-Ritual-is_terminal]]
- [[eos_ai-substrate-rituals-py-RitualRegistry-_flush]]
- [[eos_ai-substrate-rituals-py-RitualRegistry-_require]]
- [[eos_ai-substrate-rituals-py-_utcnow]]

## Called By

- [[eos_ai-substrate-day_workflows-py-_advance_ritual_best_effort]]
- [[eos_ai-substrate-ritual_runner-py-finish_close_day]]
- [[eos_ai-substrate-ritual_runner-py-finish_open_day]]
- [[eos_ai-substrate-ritual_runner-py-start_close_day]]
- [[eos_ai-substrate-ritual_runner-py-start_open_day]]
- [[eos_ai-substrate-rituals-py-RitualRegistry-complete]]
- [[eos_ai-substrate-rituals-py-RitualRegistry-fail]]
