---
type: codebase-function
file: eos_ai/substrate/meet_caption_bridge.py
line: 40
generated: 2026-04-12
---

# sanitize_meeting_code

**File:** [[eos_ai-substrate-meet_caption_bridge-py]] | **Line:** 40
**Signature:** `sanitize_meeting_code(code) → str`

Sanitize a meeting code to a filesystem-safe slug.

Replaces any char outside [a-zA-Z0-9_-] with '_', clips to 64 chars.
Returns 'unknown' if the result is empty.

## Called By

- [[eos_ai-substrate-meet_caption_bridge-py-CaptionReader-__init__]]
- [[eos_ai-substrate-meet_caption_bridge-py-CaptionWriter-__init__]]
- [[eos_ai-substrate-meet_caption_bridge-py-bridge_path_for]]
