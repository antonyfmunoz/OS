---
type: codebase-class
file: eos_ai/substrate/operator_state.py
line: 71
generated: 2026-05-07
---

# OperatorMode

**File:** [[eos_ai-substrate-operator_state-py]] | **Line:** 71

Bounded operator modes.

IDLE         — node is registered but no active session/ritual
STARTING     — wake/clap received, transitioning into ACTIVE
ACTIVE       — voice session active, operator present
...

## Inherits From

- `str`
- `Enum`
