---
type: codebase-function
file: eos_ai/substrate/meet_caption_bridge.py
line: 105
generated: 2026-04-11
---

# CaptionWriter.append

**File:** [[eos_ai-substrate-meet_caption_bridge-py]] | **Line:** 105
**Signature:** `append(text) → dict[str, Any]`

**Class:** [[eos_ai-substrate-meet_caption_bridge-py-CaptionWriter]]

Append a single caption line. Never raises on normal inputs.

Returns a status dict: {"status","event_id","path","detail"}.

## Calls

- [[eos_ai-substrate-meet_caption_bridge-py-_ensure_root]]
- [[eos_ai-substrate-meet_caption_bridge-py-compute_event_id]]
- [[eos_ai-substrate-meet_caption_bridge-py-now_iso_utc]]

## Called By

- [[eos_ai-substrate-meet_caption_bridge-py-CaptionReader-_write_persisted_offset]]
- [[eos_ai-substrate-meet_caption_bridge-py-CaptionReader-read_new]]
- [[eos_ai-substrate-meet_caption_bridge-py-CaptionWriter-append_many]]
- [[eos_ai-substrate-meet_caption_bridge-py-append_caption]]
- [[eos_ai-substrate-meet_caption_bridge-py-make_bridge_hook]]
- [[scripts-meet_caption_writer-py-main]]
