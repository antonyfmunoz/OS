---
type: codebase-file
path: eos_ai/substrate/capability_tagging.py
module: eos_ai.substrate.capability_tagging
lines: 134
size: 4930
generated: 2026-04-11
---

# eos_ai/substrate/capability_tagging.py

Capability tagging — additive pre-routing layer.

This module annotates incoming gateway requests with the set of capabilities
they would *like* a target node to have. It does NOT change routing. The
model_router and gateway continue to make their own decisions; tags live on
...

**Lines:** 134 | **Size:** 4,930 bytes

## Depends On

- [[eos_ai-substrate-capabilities-py]]

## Contains

- **fn** [[eos_ai-substrate-capability_tagging-py-_text]]`(request) → str`
- **fn** [[eos_ai-substrate-capability_tagging-py-_comm_type]]`(request) → str`
- **fn** [[eos_ai-substrate-capability_tagging-py-_channel]]`(request) → str`
- **fn** [[eos_ai-substrate-capability_tagging-py-_is_voice]]`(request) → bool`
- **fn** [[eos_ai-substrate-capability_tagging-py-_is_browser]]`(request) → bool`
- **fn** [[eos_ai-substrate-capability_tagging-py-_is_workstation]]`(request) → bool`
- **fn** [[eos_ai-substrate-capability_tagging-py-_is_long_running]]`(request) → bool`
- **fn** [[eos_ai-substrate-capability_tagging-py-tag_request]]`(request) → list[str]`

## Import Statements

```python
from __future__ import annotations
from typing import Any
from eos_ai.substrate.capabilities import Capability
```
