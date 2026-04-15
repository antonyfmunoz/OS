---
type: codebase-class
file: eos_ai/substrate/actions.py
line: 31
generated: 2026-04-12
---

# ActionKind

**File:** [[eos_ai-substrate-actions-py]] | **Line:** 31

Canonical intents. Anything a local node might do for EOS must map to
one of these. Raw OS commands are explicitly excluded — add a new kind
here rather than smuggling shell strings through `payload`.

## Inherits From

- `str`
- `Enum`
