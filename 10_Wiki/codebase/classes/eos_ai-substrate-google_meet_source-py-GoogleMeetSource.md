---
type: codebase-class
file: eos_ai/substrate/google_meet_source.py
line: 103
generated: 2026-04-12
---

# GoogleMeetSource

**File:** [[eos_ai-substrate-google_meet_source-py]] | **Line:** 103

Real-provider transcript source for Google Meet.

Implements MeetingSourceProtocol (duck-typed). Pull-only. Thread-safe.
Never raises from ``read_utterance`` — hook errors are swallowed and
recorded in ``last_error``.
...

## Methods

- [[eos_ai-substrate-google_meet_source-py-GoogleMeetSource-__init__]]`(name) → None` — 
- [[eos_ai-substrate-google_meet_source-py-GoogleMeetSource-read_utterance]]`() → Optional[dict]` — 
- [[eos_ai-substrate-google_meet_source-py-GoogleMeetSource-close]]`() → None` — 
- [[eos_ai-substrate-google_meet_source-py-GoogleMeetSource-mode]]`() → str` — Honest attachment mode. See module docstring.
- [[eos_ai-substrate-google_meet_source-py-GoogleMeetSource-attach_hook]]`(hook) → dict[str, Any]` — Wire a live transcript hook after construction.
- [[eos_ai-substrate-google_meet_source-py-GoogleMeetSource-detach_hook]]`() → dict[str, Any]` — 
- [[eos_ai-substrate-google_meet_source-py-GoogleMeetSource-status_snapshot]]`() → dict[str, Any]` — JSON-friendly snapshot for CLI/report surfaces.
- [[eos_ai-substrate-google_meet_source-py-GoogleMeetSource-_normalize]]`(raw) → Optional[dict]` — 
- [[eos_ai-substrate-google_meet_source-py-GoogleMeetSource-from_bridge]]`(name) → 'GoogleMeetSource'` — Construct a GoogleMeetSource whose hook tails a JSONL caption bridge.
- [[eos_ai-substrate-google_meet_source-py-GoogleMeetSource-bridge_path]]`() → Optional[Any]` — Best-effort: returns the bridge JSONL path if this source is bridge-backed.
- [[eos_ai-substrate-google_meet_source-py-GoogleMeetSource-_record_event]]`(kind) → None` — 
