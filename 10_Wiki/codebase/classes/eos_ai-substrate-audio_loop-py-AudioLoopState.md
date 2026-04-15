---
type: codebase-class
file: eos_ai/substrate/audio_loop.py
line: 131
generated: 2026-04-12
---

# AudioLoopState

**File:** [[eos_ai-substrate-audio_loop-py]] | **Line:** 131

Bounded audio loop state for a single node.

The state machine is small and operator-understandable:

    INACTIVE → PRIMED → LISTENING_WINDOW → RESPONDING → COOLING_DOWN
...

## Methods

- [[eos_ai-substrate-audio_loop-py-AudioLoopState-is_open_window]]`() → bool` — 
- [[eos_ai-substrate-audio_loop-py-AudioLoopState-append_transcript]]`(entry) → None` — 
- [[eos_ai-substrate-audio_loop-py-AudioLoopState-as_dict]]`() → dict` — 
- [[eos_ai-substrate-audio_loop-py-AudioLoopState-from_dict]]`(d) → 'AudioLoopState'` — 

## Decorators

- `@dataclass`
