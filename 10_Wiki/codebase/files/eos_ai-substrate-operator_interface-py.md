---
type: codebase-file
path: eos_ai/substrate/operator_interface.py
module: eos_ai.substrate.operator_interface
lines: 349
size: 11388
generated: 2026-04-12
---

# eos_ai/substrate/operator_interface.py

Operator Interface Layer v1.

A deterministic, bounded, read-first query + command surface over
linkage_snapshot(). This layer turns "structured intelligence exposed"
into "human operator can query, filter, and act on it".
...

**Lines:** 349 | **Size:** 11,388 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]

## Contains

- **fn** [[eos_ai-substrate-operator_interface-py-_safe_snapshot]]`(node_id, meeting_id) → dict[str, Any]`
- **fn** [[eos_ai-substrate-operator_interface-py-_items]]`(snap) → list[dict[str, Any]]`
- **fn** [[eos_ai-substrate-operator_interface-py-_match]]`(item, filters) → bool`
- **fn** [[eos_ai-substrate-operator_interface-py-get_actionable_items]]`(node_id, meeting_id) → list[dict[str, Any]]`
- **fn** [[eos_ai-substrate-operator_interface-py-get_top_actionable]]`(node_id, meeting_id) → Optional[dict[str, Any]]`
- **fn** [[eos_ai-substrate-operator_interface-py-get_blocked_items]]`(node_id, meeting_id) → list[dict[str, Any]]`
- **fn** [[eos_ai-substrate-operator_interface-py-get_ready_items]]`(node_id, meeting_id) → list[dict[str, Any]]`
- **fn** [[eos_ai-substrate-operator_interface-py-get_owner_breakdown]]`(node_id, meeting_id) → dict[str, Any]`
- **fn** [[eos_ai-substrate-operator_interface-py-summarize]]`(node_id, meeting_id) → dict[str, Any]`
- **fn** [[eos_ai-substrate-operator_interface-py-_get_summary]]`(node_id, meeting_id) → Optional['mi.MeetingSummary']`
- **fn** [[eos_ai-substrate-operator_interface-py-mark_resolved]]`(node_id, meeting_id) → dict[str, Any]`
- **fn** [[eos_ai-substrate-operator_interface-py-assign_owner]]`(node_id, meeting_id) → dict[str, Any]`
- **fn** [[eos_ai-substrate-operator_interface-py-refresh]]`(node_id, meeting_id) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import time
from typing import Any
from typing import Callable
from typing import Iterable
from typing import Optional
from eos_ai.substrate import meeting_intelligence as mi
```
