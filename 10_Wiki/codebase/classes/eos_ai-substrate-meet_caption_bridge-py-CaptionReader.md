---
type: codebase-class
file: eos_ai/substrate/meet_caption_bridge.py
line: 240
generated: 2026-04-12
---

# CaptionReader

**File:** [[eos_ai-substrate-meet_caption_bridge-py]] | **Line:** 240

Offset-tailing, dedupe-safe JSONL caption reader.

Reads only NEW lines since last call, tolerates partial trailing lines,
skips corrupt JSON, dedupes by event_id. Never raises from read_new().

## Methods

- [[eos_ai-substrate-meet_caption_bridge-py-CaptionReader-__init__]]`(meeting_code) → None` — 
- [[eos_ai-substrate-meet_caption_bridge-py-CaptionReader-path]]`() → Path` — 
- [[eos_ai-substrate-meet_caption_bridge-py-CaptionReader-meeting_code]]`() → str` — 
- [[eos_ai-substrate-meet_caption_bridge-py-CaptionReader-offset]]`() → int` — 
- [[eos_ai-substrate-meet_caption_bridge-py-CaptionReader-seen_count]]`() → int` — 
- [[eos_ai-substrate-meet_caption_bridge-py-CaptionReader-reset_offset]]`() → None` — Rewind to 0 (useful for tests and full-replay).
- [[eos_ai-substrate-meet_caption_bridge-py-CaptionReader-read_new]]`(max_lines) → list[dict]` — Return up to max_lines NEW, valid, deduped caption dicts.
- [[eos_ai-substrate-meet_caption_bridge-py-CaptionReader-stats]]`() → dict[str, Any]` — JSON-friendly snapshot.
- [[eos_ai-substrate-meet_caption_bridge-py-CaptionReader-drain_all]]`() → list[dict]` — Drain up to hard_cap new entries across multiple internal batches.
- [[eos_ai-substrate-meet_caption_bridge-py-CaptionReader-_offset_sidecar_path]]`() → Path` — 
- [[eos_ai-substrate-meet_caption_bridge-py-CaptionReader-_load_persisted_offset]]`() → None` — 
- [[eos_ai-substrate-meet_caption_bridge-py-CaptionReader-_write_persisted_offset]]`(value) → None` — 
