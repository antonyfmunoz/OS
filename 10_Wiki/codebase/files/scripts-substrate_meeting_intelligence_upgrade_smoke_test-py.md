---
type: codebase-file
path: scripts/substrate_meeting_intelligence_upgrade_smoke_test.py
module: scripts.substrate_meeting_intelligence_upgrade_smoke_test
lines: 235
size: 9273
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_meeting_intelligence_upgrade_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Smoke test for Meeting Intelligence Decision Upgrade.

Validates the additive bounded cognition upgrade:
  1. compute_scores produces deterministic pressure/ambiguity/priority.
  2. priority_level thresholds classify correctly (low / medium / high).
...

**Lines:** 235 | **Size:** 9,273 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]

## Contains

- **class** [[scripts-substrate_meeting_intelligence_upgrade_smoke_test-py-_FakeResult]] — 1 methods
- **fn** [[scripts-substrate_meeting_intelligence_upgrade_smoke_test-py-_patch_model]]`(outputs) → list[dict]`
- **fn** [[scripts-substrate_meeting_intelligence_upgrade_smoke_test-py-_force_model_failure]]`() → None`
- **fn** [[scripts-substrate_meeting_intelligence_upgrade_smoke_test-py-_stub_speak]]`() → list[dict]`
- **fn** [[scripts-substrate_meeting_intelligence_upgrade_smoke_test-py-_fresh_summary]]`(node_id, meeting_id) → mi.MeetingSummary`
- **fn** [[scripts-substrate_meeting_intelligence_upgrade_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import sys
from eos_ai.substrate import meeting_intelligence as mi
```
