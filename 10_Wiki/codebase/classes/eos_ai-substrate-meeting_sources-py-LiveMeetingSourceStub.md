---
type: codebase-class
file: eos_ai/substrate/meeting_sources.py
line: 117
generated: 2026-04-11
---

# LiveMeetingSourceStub

**File:** [[eos_ai-substrate-meeting_sources-py]] | **Line:** 117

Wraps a Callable[[], Optional[dict]] as a meeting source.

Designed for future real bridges (Google Meet captions WebSocket, Zoom
webhook fan-out, etc.) — the bridge supplies a hook that returns the
next utterance dict (or None). If the hook raises, the stub swallows
...

## Methods

- [[eos_ai-substrate-meeting_sources-py-LiveMeetingSourceStub-__init__]]`(name, provider, hook) → None` — 
- [[eos_ai-substrate-meeting_sources-py-LiveMeetingSourceStub-read_utterance]]`() → Optional[dict]` — 
- [[eos_ai-substrate-meeting_sources-py-LiveMeetingSourceStub-close]]`() → None` — 
