---
type: codebase-class
file: eos_ai/substrate/llm_replay.py
line: 79
generated: 2026-05-07
---

# LLMDecisionRecord

**File:** [[eos_ai-substrate-llm_replay-py]] | **Line:** 79

Full pipeline trace stored for replay.

emitted_events is the SINGLE SOURCE OF TRUTH for replay.
selected_event_indices is metadata only — never used to
recompute event emission.
...

## Decorators

- `@dataclass`
