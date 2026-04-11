---
type: codebase-function
file: eos_ai/substrate/meet_caption_bridge.py
line: 62
generated: 2026-04-11
---

# bridge_path_for

**File:** [[eos_ai-substrate-meet_caption_bridge-py]] | **Line:** 62
**Signature:** `bridge_path_for(meeting_code) → Path`

Return the JSONL file path for a given meeting code.

Creates the bridge root directory with mode 0700 if missing.

## Calls

- [[eos_ai-substrate-meet_caption_bridge-py-_ensure_root]]
- [[eos_ai-substrate-meet_caption_bridge-py-sanitize_meeting_code]]

## Called By

- [[eos_ai-substrate-meet_caption_bridge-py-CaptionReader-__init__]]
- [[eos_ai-substrate-meet_caption_bridge-py-CaptionWriter-__init__]]
