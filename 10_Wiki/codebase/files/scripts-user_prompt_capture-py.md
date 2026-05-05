---
type: codebase-file
path: scripts/user_prompt_capture.py
module: scripts.user_prompt_capture
lines: 112
size: 2820
tags: [entry-point]
generated: 2026-04-12
---

# scripts/user_prompt_capture.py

> **ENTRY POINT** — Contains `if __name__` or server start.

UserPromptSubmit hook: capture user messages into conversation files.

Pairs with wiki_stop_hook.py which captures assistant responses.
Together they create a complete conversation log.

...

**Lines:** 112 | **Size:** 2,820 bytes

## Contains

- **fn** [[scripts-user_prompt_capture-py-_read_payload]]`() → dict[str, Any]`
- **fn** [[scripts-user_prompt_capture-py-_build_header]]`(session_id, cwd, started_at) → str`
- **fn** [[scripts-user_prompt_capture-py-main]]`() → None`

## Import Statements

```python
import sys
import os
import json
from datetime import datetime
from datetime import timezone
from typing import Any
```
