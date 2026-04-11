---
type: codebase-file
path: eos_ai/substrate/meet_caption_bridge.py
module: eos_ai.substrate.meet_caption_bridge
lines: 543
size: 18717
generated: 2026-04-11
---

# eos_ai/substrate/meet_caption_bridge.py

Google Meet caption JSONL bridge.

Canonical, append-only, bounded, operator-inspectable ingestion layer for Meet
captions. Writer half (this section) is owned by Subagent A; reader half is
extended by Subagent B.
...

**Lines:** 543 | **Size:** 18,717 bytes

## Used By

- [[scripts-meet_caption_writer-py]]

## Contains

- **class** [[eos_ai-substrate-meet_caption_bridge-py-CaptionWriter]] — 5 methods
- **class** [[eos_ai-substrate-meet_caption_bridge-py-BridgeReadError]] — 0 methods
- **class** [[eos_ai-substrate-meet_caption_bridge-py-CaptionReader]] — 12 methods
- **fn** [[eos_ai-substrate-meet_caption_bridge-py-sanitize_meeting_code]]`(code) → str`
- **fn** [[eos_ai-substrate-meet_caption_bridge-py-_ensure_root]]`(root) → Path`
- **fn** [[eos_ai-substrate-meet_caption_bridge-py-bridge_path_for]]`(meeting_code) → Path`
- **fn** [[eos_ai-substrate-meet_caption_bridge-py-compute_event_id]]`(ts, text, speaker, meeting_code) → str`
- **fn** [[eos_ai-substrate-meet_caption_bridge-py-now_iso_utc]]`() → str`
- **fn** [[eos_ai-substrate-meet_caption_bridge-py-append_caption]]`(meeting_code, text) → dict[str, Any]`
- **fn** [[eos_ai-substrate-meet_caption_bridge-py-make_bridge_hook]]`(meeting_code) → Callable[[], Optional[dict]]`

## Import Statements

```python
from __future__ import annotations
import hashlib
import json
import os
import re
import threading
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
from typing import Iterable
from typing import Optional
from collections import deque
from typing import Callable
```
