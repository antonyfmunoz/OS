---
type: codebase-class
file: eos_ai/substrate/meeting_sources.py
line: 65
generated: 2026-05-07
---

# FakeMeetingSource

**File:** [[eos_ai-substrate-meeting_sources-py]] | **Line:** 65

Deterministic finite meeting source for tests.

Pops one utterance per ``read_utterance()`` call from an internal deque.
Returns ``None`` when empty. Thread-safe via an RLock. Never raises.

## Methods

- [[eos_ai-substrate-meeting_sources-py-FakeMeetingSource-__init__]]`(name, provider, utterances) → None` — 
- [[eos_ai-substrate-meeting_sources-py-FakeMeetingSource-read_utterance]]`() → Optional[dict]` — 
- [[eos_ai-substrate-meeting_sources-py-FakeMeetingSource-close]]`() → None` — 
- [[eos_ai-substrate-meeting_sources-py-FakeMeetingSource-extend]]`(utterances) → None` — Test helper: append more utterances to the queue.
