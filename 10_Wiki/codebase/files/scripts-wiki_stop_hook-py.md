---
type: codebase-file
path: scripts/wiki_stop_hook.py
module: scripts.wiki_stop_hook
lines: 168
size: 4864
tags: [entry-point]
generated: 2026-04-11
---

# scripts/wiki_stop_hook.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Stop hook: capture real conversation content to session file.

Creates the session file lazily on first real content write.
Only writes if there is meaningful assistant text to capture.
Preserves idempotency via timestamp dedup check.
...

**Lines:** 168 | **Size:** 4,864 bytes

## Contains

- **fn** [[scripts-wiki_stop_hook-py-_read_payload]]`() → dict[str, Any]`
- **fn** [[scripts-wiki_stop_hook-py-_extract_assistant_text]]`(hook_input) → str`
- **fn** [[scripts-wiki_stop_hook-py-_build_header]]`(session_id, cwd, started_at) → str`
- **fn** [[scripts-wiki_stop_hook-py-_build_entry]]`(iso_ts, stop_reason, assistant_text, has_user_entry) → str`
- **fn** [[scripts-wiki_stop_hook-py-main]]`() → None`

## Import Statements

```python
import sys
import os
import json
from datetime import datetime
from datetime import timezone
from typing import Any
```
