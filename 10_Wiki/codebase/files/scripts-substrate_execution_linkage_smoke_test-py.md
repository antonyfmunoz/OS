---
type: codebase-file
path: scripts/substrate_execution_linkage_smoke_test.py
module: scripts.substrate_execution_linkage_smoke_test
lines: 234
size: 7524
tags: [entry-point]
generated: 2026-04-11
---

# scripts/substrate_execution_linkage_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Smoke test for Execution Linkage Layer v1.

Validates additive, bounded, deterministic projection of intelligence
state into structured ActionableItems with execution readiness
classification. No hot-path changes; no task execution.
...

**Lines:** 234 | **Size:** 7,524 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]

## Contains

- **fn** [[scripts-substrate_execution_linkage_smoke_test-py-_fresh_summary]]`() → mi.MeetingSummary`
- **fn** [[scripts-substrate_execution_linkage_smoke_test-py-_commitment]]`(text, owner, conf, resolved) → dict`
- **fn** [[scripts-substrate_execution_linkage_smoke_test-py-test_commitments_and_open_loops_project]]`() → None`
- **fn** [[scripts-substrate_execution_linkage_smoke_test-py-test_readiness_states]]`() → None`
- **fn** [[scripts-substrate_execution_linkage_smoke_test-py-test_cap_enforced]]`() → None`
- **fn** [[scripts-substrate_execution_linkage_smoke_test-py-test_report_block_has_linkage_fields]]`() → None`
- **fn** [[scripts-substrate_execution_linkage_smoke_test-py-test_report_block_fallback_has_linkage_fields]]`() → None`
- **fn** [[scripts-substrate_execution_linkage_smoke_test-py-test_malformed_input_safe]]`() → None`
- **fn** [[scripts-substrate_execution_linkage_smoke_test-py-test_hot_path_clean]]`() → None`
- **fn** [[scripts-substrate_execution_linkage_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import json
import subprocess
import sys
import time
from eos_ai.substrate import meeting_intelligence as mi
```
