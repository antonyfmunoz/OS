---
type: codebase-function
file: eos_ai/substrate/meet_caption_bridge.py
line: 305
generated: 2026-04-12
---

# CaptionReader.read_new

**File:** [[eos_ai-substrate-meet_caption_bridge-py]] | **Line:** 305
**Signature:** `read_new(max_lines) → list[dict]`

**Class:** [[eos_ai-substrate-meet_caption_bridge-py-CaptionReader]]

Return up to max_lines NEW, valid, deduped caption dicts.

Partial trailing lines are preserved for next call. Corrupt lines
are skipped and counted. Never raises.

## Calls

- [[eos_ai-substrate-meet_caption_bridge-py-CaptionReader-_write_persisted_offset]]
- [[eos_ai-substrate-meet_caption_bridge-py-CaptionWriter-append]]

## Called By

- [[eos_ai-substrate-meet_caption_bridge-py-CaptionReader-drain_all]]
- [[eos_ai-substrate-meet_caption_bridge-py-make_bridge_hook]]
