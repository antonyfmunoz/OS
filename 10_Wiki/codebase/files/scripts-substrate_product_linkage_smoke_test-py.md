---
type: codebase-file
path: scripts/substrate_product_linkage_smoke_test.py
module: scripts.substrate_product_linkage_smoke_test
lines: 378
size: 12024
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_product_linkage_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Smoke test for Product Linkage Layer v1.

Validates the stable, versioned, product-facing contract built on top of
the intelligence layers. Pure transform; no execution, no side effects.

...

**Lines:** 378 | **Size:** 12,024 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]

## Contains

- **fn** [[scripts-substrate_product_linkage_smoke_test-py-_fresh_summary]]`() → mi.MeetingSummary`
- **fn** [[scripts-substrate_product_linkage_smoke_test-py-_commitment]]`(text, owner, conf, resolved) → dict`
- **fn** [[scripts-substrate_product_linkage_smoke_test-py-_assert]]`(cond, msg) → None`
- **fn** [[scripts-substrate_product_linkage_smoke_test-py-test_01_empty_snapshot_shape]]`() → None`
- **fn** [[scripts-substrate_product_linkage_smoke_test-py-test_02_sub_block_schemas_on_empty]]`() → None`
- **fn** [[scripts-substrate_product_linkage_smoke_test-py-test_03_realistic_populated_snapshot]]`() → None`
- **fn** [[scripts-substrate_product_linkage_smoke_test-py-test_04_actionable_cap_respected]]`() → None`
- **fn** [[scripts-substrate_product_linkage_smoke_test-py-test_05_malformed_input_degrades_safely]]`() → None`
- **fn** [[scripts-substrate_product_linkage_smoke_test-py-test_06_no_regression_in_intelligence_report_block]]`() → None`
- **fn** [[scripts-substrate_product_linkage_smoke_test-py-test_07_entry_points_work]]`() → None`
- **fn** [[scripts-substrate_product_linkage_smoke_test-py-test_08_json_serializable]]`() → None`
- **fn** [[scripts-substrate_product_linkage_smoke_test-py-test_09_hot_path_files_clean]]`() → None`
- **fn** [[scripts-substrate_product_linkage_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import json
import subprocess
import sys
import time
from eos_ai.substrate import meeting_intelligence as mi
```
