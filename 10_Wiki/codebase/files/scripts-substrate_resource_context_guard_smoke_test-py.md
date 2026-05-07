---
type: codebase-file
path: scripts/substrate_resource_context_guard_smoke_test.py
module: scripts.substrate_resource_context_guard_smoke_test
lines: 799
size: 30305
tags: [entry-point]
generated: 2026-05-07
---

# scripts/substrate_resource_context_guard_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Resource Guard, Workload Classification & Context Lifecycle — smoke test.

Proves that:
  1.  "what backend are you using" → lightweight.
  2.  "fix this bug in the auth system" → heavyweight.
...

**Lines:** 799 | **Size:** 30,305 bytes

## Contains

- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-check]]`(name, cond, detail) → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-_header]]`(msg) → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-_reset_env]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-test_workload_lightweight_question]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-test_workload_heavyweight_fix]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-test_workload_standard_draft]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-test_workload_workflow_kind_override]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-test_workload_hello_lightweight]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-test_workload_short_text_lightweight]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-test_workload_force_override]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-test_workload_weight_order]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-test_resource_snapshot_keys]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-test_guard_disabled_default]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-test_guard_enabled_high_pressure_heavyweight]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-test_guard_product_mode_override]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-test_guard_moderate_force_local]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-test_guard_low_pressure_allowed]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-test_low_message_count_low_pressure]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-test_high_count_degradation_high_pressure]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-test_all_signals_max_pressure]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-test_checkpoint_builds_correctly]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-test_restore_from_checkpoint]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-test_no_hot_path_imports]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-test_no_daemon_or_background_thread]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-test_one_router_no_new_class]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-test_no_second_cognition_pipeline]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-test_all_modules_have_all_exports]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-test_session_control_maybe_auto_clear_functional]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-test_resource_guard_enabled_toggle]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-test_context_guard_enabled_toggle]]`() → None`
- **fn** [[scripts-substrate_resource_context_guard_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import os
import sys
```
