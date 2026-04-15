---
type: codebase-file
path: scripts/substrate_temporal_intelligence_smoke_test.py
module: scripts.substrate_temporal_intelligence_smoke_test
lines: 315
size: 11330
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_temporal_intelligence_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Smoke test for Temporal Intelligence Layer v1.

Validates the additive bounded upgrade layered on top of Resolution
Intelligence. Time is simulated by directly manipulating `created_at` /
`last_followup_prompt_ts` values so the test remains deterministic and
...

**Lines:** 315 | **Size:** 11,330 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]

## Contains

- **fn** [[scripts-substrate_temporal_intelligence_smoke_test-py-_fresh_summary]]`() → mi.MeetingSummary`
- **fn** [[scripts-substrate_temporal_intelligence_smoke_test-py-_commitment]]`(text, created_at, resolved) → dict`
- **fn** [[scripts-substrate_temporal_intelligence_smoke_test-py-test_stale_detection]]`() → None`
- **fn** [[scripts-substrate_temporal_intelligence_smoke_test-py-test_resolved_not_stale]]`() → None`
- **fn** [[scripts-substrate_temporal_intelligence_smoke_test-py-test_follow_up_prioritizes_stale]]`() → None`
- **fn** [[scripts-substrate_temporal_intelligence_smoke_test-py-test_follow_up_cooldown_suppresses_repeats]]`() → None`
- **fn** [[scripts-substrate_temporal_intelligence_smoke_test-py-test_next_followup_eligible_ts]]`() → None`
- **fn** [[scripts-substrate_temporal_intelligence_smoke_test-py-test_stale_open_loops_count]]`() → None`
- **fn** [[scripts-substrate_temporal_intelligence_smoke_test-py-test_temporal_health_values]]`() → None`
- **fn** [[scripts-substrate_temporal_intelligence_smoke_test-py-test_report_block_temporal_fields]]`() → None`
- **fn** [[scripts-substrate_temporal_intelligence_smoke_test-py-test_report_block_defaults_on_missing_meeting]]`() → None`
- **fn** [[scripts-substrate_temporal_intelligence_smoke_test-py-test_bad_input_never_raises]]`() → None`
- **fn** [[scripts-substrate_temporal_intelligence_smoke_test-py-test_caps_still_enforced]]`() → None`
- **fn** [[scripts-substrate_temporal_intelligence_smoke_test-py-test_hot_path_clean]]`() → None`
- **fn** [[scripts-substrate_temporal_intelligence_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import subprocess
import sys
import time
from eos_ai.substrate import meeting_intelligence as mi
```
