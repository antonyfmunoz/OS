---
type: codebase-file
path: eos_ai/substrate/context_lifecycle.py
module: eos_ai.substrate.context_lifecycle
lines: 314
size: 10902
generated: 2026-05-07
---

# eos_ai/substrate/context_lifecycle.py

Context lifecycle — pressure-aware session maintenance with checkpoint/restore.

Purpose
-------
Replaces message-count-based ``/clear`` decisions with multi-signal context
...

**Lines:** 314 | **Size:** 10,902 bytes

## Used By

- [[eos_ai-substrate-discord_text_transport-py]]

## Contains

- **fn** [[eos_ai-substrate-context_lifecycle-py-_pressure_threshold]]`() → float`
- **fn** [[eos_ai-substrate-context_lifecycle-py-_guard_enabled]]`() → bool`
- **fn** [[eos_ai-substrate-context_lifecycle-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-context_lifecycle-py-_has_degradation_markers]]`(text) → bool`
- **fn** [[eos_ai-substrate-context_lifecycle-py-detect_context_pressure]]`(session_name) → dict[str, Any]`
- **fn** [[eos_ai-substrate-context_lifecycle-py-build_context_checkpoint]]`(session_name) → dict[str, Any]`
- **fn** [[eos_ai-substrate-context_lifecycle-py-restore_from_checkpoint]]`(checkpoint) → dict[str, Any]`
- **fn** [[eos_ai-substrate-context_lifecycle-py-maybe_clear_and_restore]]`(session_name, target, mode) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import os
import re
import sys
from datetime import datetime
from datetime import timezone
from typing import Any
```
