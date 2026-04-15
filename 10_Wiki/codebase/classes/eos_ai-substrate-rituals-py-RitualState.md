---
type: codebase-class
file: eos_ai/substrate/rituals.py
line: 36
generated: 2026-04-12
---

# RitualState

**File:** [[eos_ai-substrate-rituals-py]] | **Line:** 36

Canonical lifecycle for any ritual. Specific kinds may only use a subset.

    PENDING   → INITIATED → GATHERING → BRIEFING → HANDOFF → COMPLETED
                                    ↘ FAILED

...

## Inherits From

- `str`
- `Enum`
