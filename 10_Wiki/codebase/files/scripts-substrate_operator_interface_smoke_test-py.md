---
type: codebase-file
path: scripts/substrate_operator_interface_smoke_test.py
module: scripts.substrate_operator_interface_smoke_test
lines: 348
size: 12056
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_operator_interface_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Smoke test for Operator Interface Layer v1.

Validates the operator query + controlled-command surface built on top
of linkage_snapshot(). Deterministic. Bounded. No automation.

...

**Lines:** 348 | **Size:** 12,056 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]

## Contains

- **fn** [[scripts-substrate_operator_interface_smoke_test-py-_commitment]]`(text, owner, conf, resolved) → dict`
- **fn** [[scripts-substrate_operator_interface_smoke_test-py-_fresh_populated]]`() → mi.MeetingSummary`
- **fn** [[scripts-substrate_operator_interface_smoke_test-py-_assert]]`(cond, msg) → None`
- **fn** [[scripts-substrate_operator_interface_smoke_test-py-test_01_summarize_empty]]`() → None`
- **fn** [[scripts-substrate_operator_interface_smoke_test-py-test_02_get_actionable_items_populated]]`() → None`
- **fn** [[scripts-substrate_operator_interface_smoke_test-py-test_03_filter_by_priority]]`() → None`
- **fn** [[scripts-substrate_operator_interface_smoke_test-py-test_04_filter_by_owner]]`() → None`
- **fn** [[scripts-substrate_operator_interface_smoke_test-py-test_05_ready_and_blocked_partition]]`() → None`
- **fn** [[scripts-substrate_operator_interface_smoke_test-py-test_06_top_actionable_is_highest_priority]]`() → None`
- **fn** [[scripts-substrate_operator_interface_smoke_test-py-test_07_owner_breakdown_counts]]`() → None`
- **fn** [[scripts-substrate_operator_interface_smoke_test-py-test_08_mark_resolved_with_selector]]`() → None`
- **fn** [[scripts-substrate_operator_interface_smoke_test-py-test_09_mark_resolved_delta_in_summary]]`() → None`
- **fn** [[scripts-substrate_operator_interface_smoke_test-py-test_10_assign_owner_updates_breakdown]]`() → None`
- **fn** [[scripts-substrate_operator_interface_smoke_test-py-test_11_refresh_returns_snapshot]]`() → None`
- **fn** [[scripts-substrate_operator_interface_smoke_test-py-test_12_json_serializable]]`() → None`
- **fn** [[scripts-substrate_operator_interface_smoke_test-py-test_13_degrades_on_empty_and_malformed]]`() → None`
- **fn** [[scripts-substrate_operator_interface_smoke_test-py-test_14_cli_subcommands_execute]]`() → None`
- **fn** [[scripts-substrate_operator_interface_smoke_test-py-test_15_hot_path_untouched]]`() → None`
- **fn** [[scripts-substrate_operator_interface_smoke_test-py-test_16_existing_linkage_surface_intact]]`() → None`
- **fn** [[scripts-substrate_operator_interface_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import json
import subprocess
import sys
import time
from eos_ai.substrate import meeting_intelligence as mi
from eos_ai.substrate import operator_interface as oi
```
