---
type: codebase-class
file: eos_ai/substrate/perception.py
line: 88
generated: 2026-05-07
---

# PerceptionRecord

**File:** [[eos_ai-substrate-perception-py]] | **Line:** 88

A single structured observation from any perception collector.

## Methods

- [[eos_ai-substrate-perception-py-PerceptionRecord-new]]`(source, summary, severity) → 'PerceptionRecord'` — Create a new PerceptionRecord with generated ID and fingerprint.
- [[eos_ai-substrate-perception-py-PerceptionRecord-to_dict]]`() → dict` — Return a JSON-safe dict. Enums serialized as their .value.
- [[eos_ai-substrate-perception-py-PerceptionRecord-from_dict]]`(d) → 'PerceptionRecord'` — Deserialize from a dict, reconstructing enums with safe defaults.

## Decorators

- `@dataclass`
