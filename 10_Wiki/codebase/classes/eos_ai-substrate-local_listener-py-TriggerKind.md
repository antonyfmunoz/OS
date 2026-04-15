---
type: codebase-class
file: eos_ai/substrate/local_listener.py
line: 74
generated: 2026-04-12
---

# TriggerKind

**File:** [[eos_ai-substrate-local_listener-py]] | **Line:** 74

Bounded set of activation causes the listener will accept.

wake_word_detected and clap_detected are intentionally *stubs* in this
pass — the substrate accepts them as bounded events but the listener does
not own any audio framework. Real detection plugs in later as a producer.

## Inherits From

- `str`
- `Enum`
