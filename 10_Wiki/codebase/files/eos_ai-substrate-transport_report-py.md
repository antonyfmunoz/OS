---
type: codebase-file
path: eos_ai/substrate/transport_report.py
module: eos_ai.substrate.transport_report
lines: 638
size: 23912
generated: 2026-04-12
---

# eos_ai/substrate/transport_report.py

Unified transport report — bounded read-only join across the local PTT,
the Discord voice transport, and the shared voice/audio/operator state.

Purpose
-------
...

**Lines:** 638 | **Size:** 23,912 bytes

## Used By

- [[scripts-substrate_meeting_transport_smoke_test-py]]
- [[scripts-substrate_transport_report_smoke_test-py]]

## Contains

- **fn** [[eos_ai-substrate-transport_report-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-transport_report-py-_utcnow_iso]]`() → str`
- **fn** [[eos_ai-substrate-transport_report-py-_safe]]`(call, default)`
- **fn** [[eos_ai-substrate-transport_report-py-_group_transcripts_by_source]]`(transcripts) → dict[str, int]`
- **fn** [[eos_ai-substrate-transport_report-py-unified_transport_report]]`(node_id) → dict[str, Any]`
- **fn** [[eos_ai-substrate-transport_report-py-_empty_pseudo_live]]`() → dict`
- **fn** [[eos_ai-substrate-transport_report-py-_pseudo_live_block]]`() → dict`
- **fn** [[eos_ai-substrate-transport_report-py-_empty_continuity]]`() → dict`
- **fn** [[eos_ai-substrate-transport_report-py-_empty_ingress]]`() → dict`
- **fn** [[eos_ai-substrate-transport_report-py-_empty_playback_last]]`() → dict`
- **fn** [[eos_ai-substrate-transport_report-py-_continuity_block]]`(report) → dict`
- **fn** [[eos_ai-substrate-transport_report-py-_latest_occurred_at]]`(entries) → Optional[str]`
- **fn** [[eos_ai-substrate-transport_report-py-_ingress_block]]`(report) → dict`
- **fn** [[eos_ai-substrate-transport_report-py-_playback_last_block]]`(report) → dict`
- **fn** [[eos_ai-substrate-transport_report-py-_iso_from_mtime]]`(mtime) → Optional[str]`
- **fn** [[eos_ai-substrate-transport_report-py-_attached_meeting_codes]]`(report) → set[str]`
- **fn** [[eos_ai-substrate-transport_report-py-_meet_bridges_block]]`(report) → list[dict]`
- **fn** [[eos_ai-substrate-transport_report-py-_supervision_hints_block]]`(report) → list[str]`

## Import Statements

```python
from __future__ import annotations
import sys
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Optional
```
