---
type: codebase-function
file: eos_ai/substrate/meet_caption_bridge.py
line: 470
generated: 2026-04-12
---

# make_bridge_hook

**File:** [[eos_ai-substrate-meet_caption_bridge-py]] | **Line:** 470
**Signature:** `make_bridge_hook(meeting_code) → Callable[[], Optional[dict]]`

Build a hook callable matching GoogleMeetSource's hook contract.

Each hook call returns the OLDEST not-yet-returned entry in the source
shape {"text","user_id","participant_name","metadata"} or None if the
bridge has no new data. An internal micro-queue (<= batch_size) lets
...

## Calls

- [[eos_ai-substrate-meet_caption_bridge-py-CaptionReader-read_new]]
- [[eos_ai-substrate-meet_caption_bridge-py-CaptionWriter-append]]
