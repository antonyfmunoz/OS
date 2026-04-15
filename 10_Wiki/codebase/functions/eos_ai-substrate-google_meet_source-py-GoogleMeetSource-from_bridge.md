---
type: codebase-function
file: eos_ai/substrate/google_meet_source.py
line: 286
generated: 2026-04-12
---

# GoogleMeetSource.from_bridge

**File:** [[eos_ai-substrate-google_meet_source-py]] | **Line:** 286
**Signature:** `from_bridge(name) → 'GoogleMeetSource'`

**Class:** [[eos_ai-substrate-google_meet_source-py-GoogleMeetSource]]

Construct a GoogleMeetSource whose hook tails a JSONL caption bridge.

The bridge is the canonical durable ingestion path written by
``meet_caption_bridge.CaptionWriter``. This classmethod wires a
deduped, offset-based, bounded reader hook so the source can be
...

## Decorators

- `@classmethod`
