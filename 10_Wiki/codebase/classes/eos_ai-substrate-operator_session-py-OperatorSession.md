---
type: codebase-class
file: eos_ai/substrate/operator_session.py
line: 81
generated: 2026-05-07
---

# OperatorSession

**File:** [[eos_ai-substrate-operator_session-py]] | **Line:** 81

Unified bounded operator session state for daily lifecycle management.

One record exists at a time. Created fresh on open_day; updated throughout
the day; closed at close_day with continuity fields written for the next open.

## Methods

- [[eos_ai-substrate-operator_session-py-OperatorSession-new]]`() → 'OperatorSession'` — Create a fresh OperatorSession with a new ID and current timestamps.
- [[eos_ai-substrate-operator_session-py-OperatorSession-to_dict]]`() → dict` — Return a JSON-safe dict. Enums serialized as their .value.
- [[eos_ai-substrate-operator_session-py-OperatorSession-from_dict]]`(d) → 'OperatorSession'` — Deserialize from a dict, reconstructing enums and guarding list fields.

## Decorators

- `@dataclass`
