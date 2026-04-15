---
type: codebase-class
file: eos_ai/substrate/station.py
line: 56
generated: 2026-04-12
---

# ControlMode

**File:** [[eos_ai-substrate-station-py]] | **Line:** 56

How much authority EOS has over the local station at a given moment.

OBSERVE  — station reports state only; cannot be told to act.
ASSIST   — station accepts suggestions; each action requires local confirm.
DRIVE    — station executes EOS-issued SafeActions automatically, within
...

## Inherits From

- `str`
- `Enum`
