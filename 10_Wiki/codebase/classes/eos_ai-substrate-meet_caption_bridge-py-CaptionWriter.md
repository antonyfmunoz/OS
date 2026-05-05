---
type: codebase-class
file: eos_ai/substrate/meet_caption_bridge.py
line: 89
generated: 2026-04-12
---

# CaptionWriter

**File:** [[eos_ai-substrate-meet_caption_bridge-py]] | **Line:** 89

Append-only writer for Meet caption JSONL bridge files.

## Methods

- [[eos_ai-substrate-meet_caption_bridge-py-CaptionWriter-__init__]]`(meeting_code) → None` — 
- [[eos_ai-substrate-meet_caption_bridge-py-CaptionWriter-path]]`() → Path` — 
- [[eos_ai-substrate-meet_caption_bridge-py-CaptionWriter-meeting_code]]`() → str` — 
- [[eos_ai-substrate-meet_caption_bridge-py-CaptionWriter-append]]`(text) → dict[str, Any]` — Append a single caption line. Never raises on normal inputs.
- [[eos_ai-substrate-meet_caption_bridge-py-CaptionWriter-append_many]]`(items) → dict[str, Any]` — Append many items. Each item is a dict with at least 'text'.
